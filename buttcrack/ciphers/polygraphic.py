"""Polygraphic ciphers: Playfair and Bifid.

These encrypt *groups* of letters rather than single letters, which defeats both
frequency analysis and the index of coincidence (a Playfair text has IC ~ 0.045,
much flatter than a substitution's 0.066).  They are also the point where
cryptanalysis becomes statistical rather than mechanical:

Playfair
    The key is a 5x5 grid -- 25! orderings -- so it is hill climbed exactly like
    a substitution, scoring quadgram fitness of the decryption and swapping two
    grid cells at a time.  It needs more text than substitution does: below ~100
    letters the correct grid is usually not the global optimum, and even above
    200 a couple of cell swaps can survive as noise.  Playfair also has a
    structural tell used for identification: no digraph ever repeats a letter
    ("SS" cannot occur), and J never appears.

Bifid
    Fractionates each letter into row/column coordinates and recombines them
    within a period.  The attack has to guess the period *and* the grid, so it
    hill climbs the grid for every candidate period.  It works on a few hundred
    letters and is marked experimental -- the honest failure mode is documented
    in the README.
"""

from __future__ import annotations

import random
import time
from collections import Counter
from typing import Any, Iterator

from ..lang import get_model
from ..results import Candidate
from ..search import parallel_restarts, restart_search
from ..text import A25, A26, index_of_coincidence, letters_only
from .base import EXPENSIVE, BRUTAL, Cipher, CipherInfo, CrackContext, Family


def make_grid(keyword: str, alphabet: str = A25) -> str:
    """Build the 5x5 grid as a 25-letter string (J folded into I)."""
    key = letters_only(str(keyword).upper().replace("J", "I"), alphabet)
    seen: list[str] = []
    for ch in key:
        if ch not in seen:
            seen.append(ch)
    for ch in alphabet:
        if ch not in seen:
            seen.append(ch)
    return "".join(seen[: len(alphabet)])


#: Precomputed row/column of each grid index, so the inner loop avoids divmod.
_ROW = [i // 5 for i in range(25)]
_COL = [i % 5 for i in range(25)]


def apply_grid(stream: str, grid: str, decrypt: bool = True) -> str:
    """Apply a 5x5 Playfair grid to an even-length A-Z stream.

    Functionally identical to :meth:`Playfair._apply` but avoids the dict and
    divmod work in the hot loop -- the search evaluates this hundreds of
    thousands of times, so the 1.6x matters.
    """
    pos = [0] * 26
    for i, ch in enumerate(grid):
        pos[ord(ch) - 65] = i
    step = -1 if decrypt else 1
    out: list[str] = []
    append = out.append
    n = len(stream)
    for i in range(0, n - 1, 2):
        ia = pos[ord(stream[i]) - 65]
        ib = pos[ord(stream[i + 1]) - 65]
        ra, ca, rb, cb = _ROW[ia], _COL[ia], _ROW[ib], _COL[ib]
        if ra == rb:
            append(grid[ra * 5 + (ca + step) % 5])
            append(grid[rb * 5 + (cb + step) % 5])
        elif ca == cb:
            append(grid[(ra + step) % 5 * 5 + ca])
            append(grid[(rb + step) % 5 * 5 + cb])
        else:
            append(grid[ra * 5 + cb])
            append(grid[rb * 5 + ca])
    if n % 2:
        append(stream[-1])
    return "".join(out)


def prepare_playfair(text: str) -> str:
    """Playfair's normal form: A-Z with J folded into I."""
    return letters_only(text, A26).replace("J", "I")


class Playfair(Cipher):
    """The Playfair cipher (Wheatstone/Playfair, 1854)."""

    info = CipherInfo(
        name="playfair",
        title="Playfair",
        family=Family.POLYGRAPHIC,
        key_type="keyword (5x5 grid)",
        keyspace=None,
        deterministic=False,
        min_length=50,
        cost=EXPENSIVE,
        alphabet=A25,
        aliases=("playfare", "double_playfair"),
        description="Digraph substitution on a 5x5 keyed grid. Solved by hill climbing the grid on quadgram fitness.",
        example_key="MONARCHY",
    )

    # -- transforms --------------------------------------------------------- #
    @staticmethod
    def _digraphs(stream: str, encrypt: bool) -> list[str]:
        """Split into digraphs, inserting X between doubled letters."""
        if not encrypt:
            return [stream[i : i + 2] for i in range(0, len(stream) - 1, 2)]
        out: list[str] = []
        i = 0
        while i < len(stream):
            a = stream[i]
            b = stream[i + 1] if i + 1 < len(stream) else "X"
            if a == b:
                b = "X" if a != "X" else "Q"
                i += 1
            else:
                i += 2
            out.append(a + b)
        return out

    def _apply(self, stream: str, grid: str, decrypt: bool) -> str:
        """The three Playfair rules: same row, same column, or rectangle.

        Encryption steps one cell forward (right / down); decryption steps back.
        A rectangle always swaps the columns of the two letters and keeps their
        rows, which is self-inverse.
        """
        if not decrypt:
            # Encryption needs the digraph splitting rule, so it keeps the
            # explicit loop; decryption (the hot path) uses the shared fast grid.
            pos = {ch: i for i, ch in enumerate(grid)}
            pairs = self._digraphs(stream, encrypt=True)
            out: list[str] = []
            for pair in pairs:
                a = pair[0]
                b = pair[1] if len(pair) > 1 else "X"
                ra, ca = divmod(pos.get(a, 0), 5)
                rb, cb = divmod(pos.get(b, 0), 5)
                if ra == rb:
                    nra, nca, nrb, ncb = ra, (ca + 1) % 5, rb, (cb + 1) % 5
                elif ca == cb:
                    nra, nca, nrb, ncb = (ra + 1) % 5, ca, (rb + 1) % 5, cb
                else:
                    nra, nca, nrb, ncb = ra, cb, rb, ca
                out.append(grid[nra * 5 + nca] + grid[nrb * 5 + ncb])
            return "".join(out)
        return apply_grid(stream, grid, decrypt=True)

    def _apply_slow(self, stream: str, grid: str, decrypt: bool) -> str:
        pos = {ch: i for i, ch in enumerate(grid)}
        step = -1 if decrypt else 1
        out: list[str] = []
        for pair in self._digraphs(stream, encrypt=not decrypt):
            a = pair[0]
            b = pair[1] if len(pair) > 1 else "X"
            ra, ca = divmod(pos.get(a, 0), 5)
            rb, cb = divmod(pos.get(b, 0), 5)
            if ra == rb:  # same row -> shift horizontally, rows unchanged
                nra, nca, nrb, ncb = ra, (ca + step) % 5, rb, (cb + step) % 5
            elif ca == cb:  # same column -> shift vertically, columns unchanged
                nra, nca, nrb, ncb = (ra + step) % 5, ca, (rb + step) % 5, cb
            else:  # rectangle -> keep rows, swap columns
                nra, nca, nrb, ncb = ra, cb, rb, ca
            out.append(grid[nra * 5 + nca] + grid[nrb * 5 + ncb])
        return "".join(out)

    def encrypt(self, plaintext: str, key: Any = "MONARCHY") -> str:
        grid = make_grid(self._keyword(key))
        return self._apply(prepare_playfair(plaintext), grid, decrypt=False)

    def decrypt(self, ciphertext: str, key: Any = "MONARCHY") -> str:
        grid = make_grid(self._keyword(key))
        return self._apply(prepare_playfair(ciphertext), grid, decrypt=True)

    @staticmethod
    def _keyword(key: Any) -> str:
        if isinstance(key, dict):
            key = key.get("key") or key.get("grid") or ""
        if isinstance(key, (list, tuple)):
            key = "".join(str(k) for k in key)
        return str(key)

    # -- cryptanalysis ------------------------------------------------------ #
    def crack(self, ciphertext: str, ctx: CrackContext) -> Iterator[Candidate]:
        stream = prepare_playfair(ciphertext)
        if len(stream) < 4:
            return
        hint = ctx.hints.get("key")
        if hint:
            plain = self.decrypt(stream, hint)
            yield ctx.candidate(self.name, plain, {"key": str(hint)}, steps=ctx.steps, method="hint")
            return
        if len(stream) % 2:
            stream += "X"
        workers = max(1, min(ctx.workers, 4))
        # Split what is left of the budget between the workers.  Playfair is the
        # one cipher where more time reliably buys more of the key, so the slice
        # is the whole remaining budget divided by the worker count.
        remaining = max(2.0, ctx.remaining())
        per_worker = remaining / workers
        now = time.time()
        payloads = [
            (
                stream,
                (ctx.hints.get("seed", 99) + i * 6151) % (2**31 - 1),
                now + per_worker * (i + 1),
                ctx.deadline,
            )
            for i in range(workers)
        ]
        ctx.report(
            f"playfair: iterated local search over 25! grids "
            f"({workers} worker{'s' if workers > 1 else ''}, {per_worker:.0f}s each, {len(stream)} letters)"
        )
        results = parallel_restarts(_playfair_worker, payloads, workers, ctx.deadline + 2.0)
        results = [r for r in results if r]
        if not results:
            return
        results.sort(key=lambda r: (-r[1], -r[2]))
        seen = set()
        for grid, conf, fit, iterations in results:
            if grid in seen:
                continue
            seen.add(grid)
            plain = apply_grid(stream, grid, True)
            notes = {
                "ils_iterations": iterations,
                "method": "iterated local search (climb + kick) on quadgram fitness",
                "grid": " ".join(grid[i : i + 5] for i in range(0, 25, 5)),
            }
            if conf < 0.62:
                notes["caveat"] = (
                    "partial: Playfair needs ~300+ letters and a generous budget; "
                    "raise --budget or pass --hint key=WORD"
                )
            # columns=25: the grid holds 25 independent cells, and a hill climb
            # will happily fit 60 letters to a key it could not have recovered --
            # so the evidence rule asks for ~6 letters per cell before the answer
            # is called a solve rather than a plausible reading.
            yield ctx.candidate(self.name, plain, {"grid": grid}, steps=ctx.steps, columns=25, **notes)
            if len(seen) >= 3 or ctx.expired():
                break

    def likelihood(self, text: str, ctx: CrackContext) -> float:
        """Playfair's structural tells: even length, no J, no doubled digraph letters."""
        stream = prepare_playfair(text)
        n = len(stream)
        if n < 40:
            return 0.0
        ic = index_of_coincidence(stream)
        # Flatter than a monoalphabetic cipher, but not random.
        ic_fit = max(0.0, min(1.0, (0.062 - ic) / (0.062 - 0.038)))
        doubled = sum(1 for i in range(0, n - 1, 2) if stream[i] == stream[i + 1])
        no_doubles = 1.0 if doubled == 0 else max(0.0, 1.0 - doubled / (n / 2))
        fit = ctx.model.ngram_score(stream)
        unreadable = max(0.0, min(1.0, (-5.0 - fit) / 2.0))
        return round(0.35 * ic_fit + 0.35 * no_doubles + 0.30 * unreadable, 4)


#: Playfair search tuning.  Every number here was measured on a 1,600-letter
#: ciphertext; see :func:`_playfair_worker` for the figures.
PLAYFAIR_SEED_WINDOW = 400     #: characters scored while the population is still noise
PLAYFAIR_POLISH_FITNESS = -5.6 #: switch to scoring the whole text past this point
PLAYFAIR_POPULATION = 12       #: grids kept alive at once
PLAYFAIR_STAGNATION = 25       #: generations without progress before the tail is reseeded


def _playfair_worker(payload: tuple) -> tuple:
    """One worker's Playfair search: a genetic algorithm over 5x5 grids.

    Why not hill climbing.  Measured on a 1,600-letter ciphertext the true grid
    scores -4.29 per character and a random grid -7.73.  A first-improvement
    climb from a random grid converges in 0.4 s to about -6.5 with only ~5 of the
    25 cells usable by the truth, because one misplaced cell costs ~0.9 per
    character -- five times what a wrong substitution alphabet costs -- so the
    truth's basin is barely three swaps wide.  A climb started *from* the truth
    with three cells scrambled recovers it in 0.2 s; a climb started anywhere
    else never sees it.  Iterated local search (climb, kick with two to four
    swaps, keep the kick if the new optimum is better) walks between neighbouring
    basins and still plateaus near -6.2.

    What works is crossover.  Local optima are wrong about *different* cells, so
    recombining two of them assembles grids neither parent can reach by swapping.
    Measured: a population of 12-16 with uniform crossover, occasional mutation
    and tail reseeding takes the best fitness from the -6.2 iterated-local-search
    plateau to about -5.4 in 45 s, which is a reading that is recognisably the
    plaintext rather than noise.

    The scoring window grows with the answer.  While the population is still
    noise, 400 characters rank grids just as well as the whole text and cost
    about a third as much per evaluation; once the best reading passes
    ``PLAYFAIR_POLISH_FITNESS`` the whole text is scored instead, because the
    last few cells need every digraph to decide them.  A final steepest-ascent
    pass over the full text cleans up what the genetic algorithm left behind.

    Runs until the deadline in the payload, so the engine keeps control of the
    total budget.
    """
    stream, seed, deadline, hard_deadline = payload
    model = get_model()
    rng = random.Random(seed)
    n = len(stream)
    pairs = [(x, y) for x in range(25) for y in range(x + 1, 25)]

    def evaluator(window: int):
        return lambda grid: model.ngram_score(  # noqa: E731
            apply_grid(stream, grid, True), normalise=False, max_chars=window
        )

    evaluate = evaluator(min(n, PLAYFAIR_SEED_WINDOW))

    def climb(key: list[str], score, max_passes: int = 40) -> tuple[list[str], float]:
        """First-improvement hill climb: cheap, and good enough to rank grids."""
        cur = score("".join(key))
        for _ in range(max_passes):
            if time.time() > hard_deadline:
                break
            rng.shuffle(pairs)
            improved = False
            for x, y in pairs:
                key[x], key[y] = key[y], key[x]
                value = score("".join(key))
                if value > cur + 1e-12:
                    cur, improved = value, True
                    break
                key[x], key[y] = key[y], key[x]
            if not improved:
                break
        return key, cur

    def steepest(key: list[str], score, max_passes: int = 12) -> tuple[list[str], float]:
        """Best-improvement climb: 300 evaluations a step, but it fixes the last cells."""
        cur = score("".join(key))
        for _ in range(max_passes):
            if time.time() > hard_deadline:
                break
            best_pair, best_value = None, cur
            for x, y in pairs:
                key[x], key[y] = key[y], key[x]
                value = score("".join(key))
                key[x], key[y] = key[y], key[x]
                if value > best_value + 1e-12:
                    best_pair, best_value = (x, y), value
            if best_pair is None:
                break
            x, y = best_pair
            key[x], key[y] = key[y], key[x]
            cur = best_value
        return key, cur

    def crossover(a: list[str], b: list[str]) -> list[str]:
        """Uniform crossover of two grids, repaired into a permutation of A25."""
        child = [a[i] if rng.random() < 0.5 else b[i] for i in range(25)]
        seen: set[str] = set()
        duplicates: list[int] = []
        for i, ch in enumerate(child):
            if ch in seen:
                duplicates.append(i)
            else:
                seen.add(ch)
        missing = [c for c in A25 if c not in seen]
        rng.shuffle(missing)
        for i, ch in zip(duplicates, missing):
            child[i] = ch
        if rng.random() < 0.3:  # mutation keeps the population from collapsing
            x, y = rng.sample(range(25), 2)
            child[x], child[y] = child[y], child[x]
        return child

    # Seed the population, but never spend more than a third of the slice on it:
    # a worker given five seconds still has to run some generations.
    slice_seconds = max(1.0, deadline - time.time())
    # Keep a quarter of the slice for the polish: the genetic algorithm ranks
    # grids well but the last few cells need a best-improvement scan over the
    # whole text, and that scan is useless if the budget is already gone.
    ga_deadline = deadline - max(2.0, 0.25 * slice_seconds)
    size = max(6, min(PLAYFAIR_POPULATION, int(slice_seconds / 2.5)))
    population: list[list] = []
    while len(population) < size and time.time() < deadline:
        grid, fit = climb(list(rng.sample(A25, 25)), evaluate)
        population.append([fit, grid])
    if not population:
        return "", 0.0, -99.0, 0
    population.sort(key=lambda entry: -entry[0])
    best_fit = population[0][0]
    full_window = False
    generations = 0
    stagnant = 0

    while time.time() < ga_deadline:
        generations += 1
        elite = min(6, len(population))
        parent_a = population[rng.randrange(elite)][1]
        parent_b = population[rng.randrange(len(population))][1]
        if stagnant and stagnant % 12 == 0:
            # Iterated-local-search move: kick the best grid instead of crossing.
            child = list(population[0][1])
            for _ in range(rng.choice((2, 3, 4))):
                x, y = rng.sample(range(25), 2)
                child[x], child[y] = child[y], child[x]
        else:
            child = crossover(parent_a, parent_b)
        child, child_fit = climb(child, evaluate)
        if child_fit > population[-1][0]:
            population[-1] = [child_fit, child]
            population.sort(key=lambda entry: -entry[0])
        if child_fit > best_fit + 1e-9:
            best_fit, stagnant = child_fit, 0
            if not full_window and best_fit > PLAYFAIR_POLISH_FITNESS and n > PLAYFAIR_SEED_WINDOW:
                # Close enough that the tail of the text is evidence, not noise.
                full_window = True
                evaluate = evaluator(n)
                population = [[evaluate("".join(entry[1])), entry[1]] for entry in population]
                population.sort(key=lambda entry: -entry[0])
                best_fit = population[0][0]
        else:
            stagnant += 1
            if stagnant >= PLAYFAIR_STAGNATION:
                stagnant = 0
                for i in range(len(population) // 2, len(population)):
                    if time.time() > deadline:
                        break
                    grid, fit = climb(list(rng.sample(A25, 25)), evaluate)
                    population[i] = [fit, grid]
                population.sort(key=lambda entry: -entry[0])
                best_fit = population[0][0]

    # Final pass on the whole text: the genetic algorithm ranks well, but the
    # last two or three cells want every digraph and a best-improvement scan.
    # The top few grids are all polished, since their scores on the short window
    # are close enough that the ranking can be wrong about which one is really
    # nearest the truth.
    polish = evaluator(n)
    best_key, best_fit = population[0][1], polish("".join(population[0][1]))
    for entry in population[:3]:
        if time.time() > deadline - 0.5:
            break
        key, fit = steepest(list(entry[1]), polish, max_passes=12)
        if fit > best_fit:
            best_key, best_fit = key, fit
    if not full_window:
        best_fit = polish("".join(best_key))
    plain = apply_grid(stream, "".join(best_key), True)
    return "".join(best_key), model.score(plain).confidence, best_fit, generations


class Bifid(Cipher):
    """Bifid (Delastelle): fractionated coordinates recombined within a period."""

    info = CipherInfo(
        name="bifid",
        title="Bifid",
        family=Family.POLYGRAPHIC,
        key_type="keyword + period",
        deterministic=False,
        min_length=80,
        cost=BRUTAL,
        alphabet=A25,
        description="Each letter becomes (row, column); the coordinates are recombined within a period. Experimental solver.",
        example_key={"key": "MONARCHY", "period": 7},
    )
    max_period = 14

    def _params(self, key: Any) -> tuple[str, int]:
        if isinstance(key, dict):
            return make_grid(str(key.get("key", ""))), int(key.get("period", 7))
        if isinstance(key, (tuple, list)):
            return make_grid(str(key[0])), int(key[1])
        return make_grid(str(key)), 7

    def _coords(self, stream: str, grid: str) -> list[tuple[int, int]]:
        pos = {ch: i for i, ch in enumerate(grid)}
        return [divmod(pos.get(c, 0), 5) for c in stream]

    def encrypt(self, plaintext: str, key: Any = None) -> str:
        grid, period = self._params(key or {"key": "MONARCHY", "period": 7})
        stream = prepare_playfair(plaintext)
        out: list[str] = []
        for start in range(0, len(stream), period):
            block = stream[start : start + period]
            coords = self._coords(block, grid)
            # Fractionation: write *all* the row coordinates, then all the column
            # coordinates, and read the result off in pairs again.  Interleaving
            # them (r1 c1 r2 c2 ...) would pair each row with its own column and
            # reproduce the plaintext -- Bifid would be the identity cipher.
            digits = [r for r, _ in coords] + [c for _, c in coords]
            pairs = [(digits[i], digits[i + 1]) for i in range(0, len(digits) - 1, 2)]
            out.append("".join(grid[r * 5 + c] for r, c in pairs))
        return "".join(out)

    def decrypt(self, ciphertext: str, key: Any = None) -> str:
        grid, period = self._params(key or {"key": "MONARCHY", "period": 7})
        return self._decrypt_grid(prepare_playfair(ciphertext), grid, period)

    def _decrypt_grid(self, stream: str, grid: str, period: int) -> str:
        """Decrypt against an already-built grid.

        Kept separate from :meth:`decrypt` because the hill climber calls it
        thousands of times and must not pay for keyword parsing and grid
        construction on every evaluation.
        """
        pos = {ch: i for i, ch in enumerate(grid)}
        out: list[str] = []
        for start in range(0, len(stream), period):
            block = stream[start : start + period]
            digits: list[int] = []
            for ch in block:
                row, col = divmod(pos.get(ch, 0), 5)
                digits.append(row)
                digits.append(col)
            half = (len(digits) + 1) // 2
            rows, cols = digits[:half], digits[half:]
            for i in range(half):
                out.append(grid[rows[i] * 5 + (cols[i] if i < len(cols) else 0)])
        return "".join(out)

    def crack(self, ciphertext: str, ctx: CrackContext) -> Iterator[Candidate]:
        stream = prepare_playfair(ciphertext)
        if len(stream) < self.info.min_length:
            return
        results: list[Candidate] = []
        hint = ctx.hints.get("key")
        hint_key: Any = None
        hint_period = ctx.hints.get("period")
        if isinstance(hint, dict):
            hint_key = hint.get("key") or hint.get("grid")
            hint_period = hint.get("period", hint_period)
        elif hint:
            hint_key = hint
        if hint_key:
            # A Bifid key is a grid *and* a period.  With the grid handed over the
            # only thing left to try is the period, so try them all and let the
            # scorer pick -- that is a dozen decryptions instead of a hill climb.
            text = str(hint_key)
            grid = text if len(set(text)) == 25 else make_grid(text)
            periods_hint = [int(hint_period)] if hint_period else list(range(2, self.max_period + 1))
            for period in periods_hint:
                plain = self._decrypt_grid(stream, grid, period)
                yield ctx.candidate(
                    self.name,
                    plain,
                    {"key": grid, "period": period},
                    steps=ctx.steps,
                    columns=36,
                    period=period,
                    method="hint",
                )
            return
        periods = range(2, self.max_period + 1)
        for period in periods:
            # Bifid needs both the period and the grid, so the search is
            # period x restarts x climb.  Keep it bounded and honest about it.
            if ctx.expired() or ctx.remaining() < 1.5:
                break
            if len(stream) < period * 8:
                continue
            restarts = 4 if len(stream) >= 300 else 8
            payloads = [
                (stream, restarts, (ctx.hints.get("seed", 7) + i * 31 + period) % (2**31 - 1), period, 2500)
                for i in range(max(1, min(ctx.workers, 2)))
            ]
            found = parallel_restarts(_bifid_worker, payloads, len(payloads), ctx.deadline)
            found = [f for f in found if f]
            if not found:
                continue
            found.sort(key=lambda f: -f[1])
            grid, conf, fit = found[0]
            plain = self._decrypt_grid(stream, grid, period)
            results.append(
                ctx.candidate(
                    self.name,
                    plain,
                    {"key": grid, "period": period},
                    steps=ctx.steps,
                    columns=36,
                    period=period,
                    method="grid hill climbing per period (experimental)",
                )
            )
        results.sort(key=Candidate.sort_key)
        yield from results

    def likelihood(self, text: str, ctx: CrackContext) -> float:
        stream = prepare_playfair(text)
        if len(stream) < 60:
            return 0.0
        ic = index_of_coincidence(stream)
        # Bifid flattens IC like a polyalphabetic cipher but keeps J out.
        ic_fit = max(0.0, min(1.0, (0.062 - ic) / (0.062 - 0.038)))
        fit = ctx.model.ngram_score(stream)
        unreadable = max(0.0, min(1.0, (-5.0 - fit) / 2.0))
        return round(0.5 * ic_fit * unreadable, 4)


def _bifid_worker(payload: tuple) -> tuple:
    stream, restarts, seed, period, max_evals = payload
    model = get_model()
    rng = random.Random(seed)
    bifid = Bifid()
    grid, plain, fit, conf, evals, used = restart_search(
        stream,
        fitness=model.search_fitness,
        confidence=lambda t: model.score(t).confidence,
        apply_key=lambda text, key: Bifid()._decrypt_grid(text, "".join(key), period),
        restarts=restarts,
        rng=rng,
        alphabet=A25,
        max_evals=max_evals,
    )
    return "".join(grid), conf, fit
