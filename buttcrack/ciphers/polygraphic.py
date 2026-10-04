"""Polygraphic ciphers: Playfair and Bifid.

These encrypt *groups* of letters rather than single letters, which defeats both
frequency analysis and the index of coincidence (a Playfair text has IC ~ 0.045,
much flatter than a substitution's 0.066).  They are also the point where
cryptanalysis becomes statistical rather than mechanical:

Playfair
    The key is a 5x5 grid -- 25! orderings -- so it is searched statistically,
    scoring quadgram fitness of the decryption and swapping two grid cells at a
    time.  Simulated annealing explores broadly while a compact genetic search
    recombines promising grids; keeping the best of both avoids making a single
    search landscape responsible for every ciphertext.  It needs more text than
    substitution does: below ~100 letters the correct grid is usually not the
    global optimum, and even above 200 a couple of cell swaps can survive as
    noise.  Playfair also has a structural tell used for identification: no
    digraph ever repeats a letter ("SS" cannot occur), and J never appears.

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
from collections.abc import Iterator
from typing import Any

from ..lang import get_model
from ..results import Candidate
from ..search import parallel_restarts, restart_search
from ..text import A25, A26, index_of_coincidence, letters_only
from .base import BRUTAL, EXPENSIVE, Cipher, CipherInfo, CrackContext, Family


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
        description="Digraph substitution on a 5x5 keyed grid. Solved by annealing and genetic search on quadgram fitness.",
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
        remaining = ctx.remaining()
        if remaining <= 0:
            return
        # Every worker receives the same hard deadline and splits its slice
        # between annealing and GA search.  Giving worker N an extra N-th slice
        # made the total search time depend on worker count and could overrun a
        # small engine budget.
        payloads = [
            (
                stream,
                (ctx.hints.get("seed", 99) + i * 6151) % (2**31 - 1),
                ctx.deadline,
                ctx.deadline,
                ctx.model.language,
            )
            for i in range(workers)
        ]
        ctx.report(
            f"playfair: annealing/GA ensemble over 25! grids "
            f"({workers} worker{'s' if workers > 1 else ''}, {remaining:.0f}s cap, {len(stream)} letters)"
        )
        results = parallel_restarts(_playfair_ensemble_worker, payloads, workers, ctx.deadline)
        results = [r for r in results if r]
        if not results:
            return
        results.sort(key=lambda r: (-r[1], -r[2]))
        seen = set()
        for grid, conf, _fit, iterations in results:
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
PLAYFAIR_SEED_WINDOW = 400  #: characters scored while the population is still noise
PLAYFAIR_POLISH_FITNESS = -5.6  #: switch to scoring the whole text past this point
PLAYFAIR_POPULATION = 12  #: grids kept alive at once
PLAYFAIR_STAGNATION = 25  #: generations without progress before the tail is reseeded


def _playfair_ensemble_worker(payload: tuple) -> tuple:
    """Run two complementary Playfair searches and return their strongest grid.

    Annealing can cross a bad local basin that an elitist population has already
    discarded.  The genetic pass, in turn, can preserve useful cell placements
    from several near misses.  They share a strict wall-clock slice rather than
    being run as two independent budget consumers.
    """
    stream, seed, deadline, hard_deadline, language = payload
    now = time.time()
    if now >= hard_deadline:
        return "", 0.0, -99.0, 0
    anneal_deadline = min(deadline, now + (deadline - now) * 0.42)
    annealed = _playfair_anneal_worker((stream, seed, anneal_deadline, hard_deadline, language))
    genetic = _playfair_worker((stream, seed + 104729, deadline, hard_deadline, language))
    return max((annealed, genetic), key=lambda result: (result[2], result[1]))


def _playfair_anneal_worker(payload: tuple) -> tuple:
    """Explore Playfair grids with a deadline-aware simulated annealing walk.

    The move is a cell swap.  Early in a run, slightly worse moves are accepted
    often enough to jump between the narrow Playfair basins; by the end it is a
    conventional local search.  The fitness window is intentionally capped
    while the grid is noise, then the winning grid is scored on the full text.
    """
    stream, seed, deadline, hard_deadline, language = payload
    model = get_model(language)
    rng = random.Random(seed)
    n = len(stream)
    window = min(n, PLAYFAIR_SEED_WINDOW)

    def fitness(grid: list[str]) -> float:
        return model.ngram_score(apply_grid(stream, "".join(grid), True), normalise=False, max_chars=window)

    started = time.time()
    total = max(0.01, min(deadline, hard_deadline) - started)
    grid = list(rng.sample(A25, 25))
    current = fitness(grid)
    best_grid, best_fit = list(grid), current
    iterations = 0
    # A handful of independent thermal walks is less prone to preserving an
    # unlucky random start than one uninterrupted walk.
    while time.time() < deadline and time.time() < hard_deadline:
        x, y = rng.sample(range(25), 2)
        grid[x], grid[y] = grid[y], grid[x]
        candidate = fitness(grid)
        progress = min(1.0, (time.time() - started) / total)
        temperature = 0.30 * (1.0 - progress) + 0.012
        delta = candidate - current
        if delta >= 0 or rng.random() < pow(2.718281828, delta / temperature):
            current = candidate
        else:
            grid[x], grid[y] = grid[y], grid[x]
        if current > best_fit:
            best_grid, best_fit = list(grid), current
        iterations += 1
        if iterations % 900 == 0 and progress < 0.85:
            grid = list(rng.sample(A25, 25))
            current = fitness(grid)

    best = "".join(best_grid)
    plain = apply_grid(stream, best, True)
    full_fit = model.ngram_score(plain, normalise=False)
    return best, model.score(plain).confidence, full_fit, iterations


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
    stream, seed, deadline, hard_deadline, language = payload
    model = get_model(language)
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
                (
                    stream,
                    restarts,
                    (ctx.hints.get("seed", 7) + i * 31 + period) % (2**31 - 1),
                    period,
                    2500,
                    ctx.model.language,
                )
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
    stream, restarts, seed, period, max_evals, language = payload
    model = get_model(language)
    rng = random.Random(seed)
    bifid = Bifid()
    grid, plain, fit, conf, evals, used = restart_search(
        stream,
        fitness=model.search_fitness,
        confidence=lambda t: model.score(t).confidence,
        apply_key=lambda text, key: bifid._decrypt_grid(text, "".join(key), period),
        restarts=restarts,
        rng=rng,
        alphabet=A25,
        max_evals=max_evals,
    )
    return "".join(grid), conf, fit


class FourSquare(Cipher):
    """Four-square (Delastelle): digraphs read across two keyed grids.

    Four 5x5 grids are laid out in a square.  The two on the diagonal hold the
    plain alphabet, the other two hold keyed alphabets.  A plaintext pair is
    located in the plain grids -- first letter top-left, second bottom-right --
    and the ciphertext is read from the *opposite corners* of the rectangle
    they make, one letter from each keyed grid.

    It fixes Playfair's two embarrassments: a doubled letter needs no padding,
    and no pair ever encrypts to itself reversed.  The cost is twice the key:
    fifty cells instead of twenty-five, which is also why the search here is
    marked experimental in the same way Playfair's is.  With either keyword
    supplied as a hint the other half is a much smaller problem.
    """

    info = CipherInfo(
        name="four_square",
        title="Four-square",
        family=Family.POLYGRAPHIC,
        key_type="two keywords",
        keyspace=None,
        deterministic=False,
        min_length=60,
        cost=BRUTAL,
        alphabet=A25,
        aliases=("foursquare", "four_square_cipher"),
        description="Digraph substitution across two keyed 5x5 grids. No padding and no reversible pairs, unlike Playfair.",
        example_key={"top": "EXAMPLE", "bottom": "KEYWORD"},
    )

    # -- key handling ------------------------------------------------------- #
    @staticmethod
    def _grids(key: Any) -> tuple[str, str]:
        """Normalise a key into the two *keyed* grids (top-right, bottom-left)."""
        if isinstance(key, dict):
            top = key.get("top") or key.get("first") or key.get("key") or ""
            bottom = key.get("bottom") or key.get("second") or ""
        elif isinstance(key, (tuple, list)) and len(key) >= 2:
            top, bottom = key[0], key[1]
        else:
            text = str(key or "")
            # One keyword is a legitimate (weaker) key: both grids share it.
            top = bottom = text
        first = top if len(set(str(top))) == 25 else make_grid(str(top))
        second = bottom if len(set(str(bottom))) == 25 else make_grid(str(bottom))
        return first, second

    def prepare(self, text: str) -> str:
        return prepare_playfair(text)

    @staticmethod
    def _pairs(stream: str) -> list[tuple[str, str]]:
        if len(stream) % 2:
            stream += "X"
        return [(stream[i], stream[i + 1]) for i in range(0, len(stream), 2)]

    # -- transforms --------------------------------------------------------- #
    def _apply(self, stream: str, top: str, bottom: str, decrypt: bool) -> str:
        plain_pos = {ch: divmod(i, 5) for i, ch in enumerate(A25)}
        out: list[str] = []
        if decrypt:
            top_pos = {ch: divmod(i, 5) for i, ch in enumerate(top)}
            bottom_pos = {ch: divmod(i, 5) for i, ch in enumerate(bottom)}
            for a, b in self._pairs(stream):
                r1, c2 = top_pos.get(a, (0, 0))
                r2, c1 = bottom_pos.get(b, (0, 0))
                out.append(A25[r1 * 5 + c1])
                out.append(A25[r2 * 5 + c2])
        else:
            for a, b in self._pairs(stream):
                r1, c1 = plain_pos.get(a, (0, 0))
                r2, c2 = plain_pos.get(b, (0, 0))
                out.append(top[r1 * 5 + c2])
                out.append(bottom[r2 * 5 + c1])
        return "".join(out)

    def encrypt(self, plaintext: str, key: Any = None) -> str:
        top, bottom = self._grids(key or self.info.example_key)
        return self._apply(self.prepare(plaintext), top, bottom, decrypt=False)

    def decrypt(self, ciphertext: str, key: Any = None) -> str:
        top, bottom = self._grids(key or self.info.example_key)
        return self._apply(self.prepare(ciphertext), top, bottom, decrypt=True)

    # -- cryptanalysis ------------------------------------------------------ #
    def crack(self, ciphertext: str, ctx: CrackContext) -> Iterator[Candidate]:
        stream = self.prepare(ciphertext)
        if len(stream) < self.info.min_length:
            return
        hint = ctx.hints.get("key")
        if hint:
            top, bottom = self._grids(hint)
            yield ctx.candidate(
                self.name,
                self._apply(stream, top, bottom, decrypt=True),
                {"top": top, "bottom": bottom},
                steps=ctx.steps,
                columns=50,
                method="hint",
            )
            return

        rng = random.Random(ctx.hints.get("seed", 90210))
        best_grids: tuple[str, str] | None = None
        best_fit = float("-inf")
        # Fifty cells is twice Playfair's key and the basin of attraction is
        # correspondingly narrower, so this is a bounded, honest attempt rather
        # than a promise: alternate climbs on one grid while the other is held,
        # which at least makes each step's effect on the fitness legible.
        while not ctx.expired() and ctx.remaining() > 0.5:
            top = "".join(rng.sample(A25, 25))
            bottom = "".join(rng.sample(A25, 25))
            fit = ctx.model.search_fitness(self._apply(stream, top, bottom, decrypt=True))
            improved = True
            while improved and not ctx.expired():
                improved = False
                for which in (0, 1):
                    grid = list(top if which == 0 else bottom)
                    for i in range(25):
                        for j in range(i + 1, 25):
                            if ctx.expired():
                                break
                            grid[i], grid[j] = grid[j], grid[i]
                            candidate_top = "".join(grid) if which == 0 else top
                            candidate_bottom = bottom if which == 0 else "".join(grid)
                            trial = ctx.model.search_fitness(
                                self._apply(stream, candidate_top, candidate_bottom, decrypt=True)
                            )
                            if trial > fit + 1e-9:
                                fit, improved = trial, True
                                top, bottom = candidate_top, candidate_bottom
                            else:
                                grid[i], grid[j] = grid[j], grid[i]
            if fit > best_fit:
                best_fit, best_grids = fit, (top, bottom)
        if best_grids is None:
            return
        top, bottom = best_grids
        yield ctx.candidate(
            self.name,
            self._apply(stream, top, bottom, decrypt=True),
            {"top": top, "bottom": bottom},
            steps=ctx.steps,
            columns=50,
            method="alternating grid hill climbing (experimental: 50 cells)",
        )

    def likelihood(self, text: str, ctx: CrackContext) -> float:
        stream = self.prepare(text)
        if len(stream) < self.info.min_length:
            return 0.0
        ic = index_of_coincidence(stream)
        # Digraphic substitution flattens single-letter statistics part way --
        # less than a polyalphabetic, more than a simple substitution -- and an
        # even length is a weak corroboration.
        flat = max(0.0, min(1.0, (0.062 - ic) / 0.020))
        return round(0.45 * flat * (1.0 if len(stream) % 2 == 0 else 0.7), 4)


#: The trifid alphabet: 26 letters plus one filler to fill the 27 cells of a
#: 3x3x3 cube.  A full stop is the traditional choice and stays out of the way
#: of the plaintext.
A27 = A26 + "."


class Trifid(Cipher):
    """Trifid (Delastelle, 1902): Bifid in three dimensions.

    Each letter becomes three coordinates in a 3x3x3 cube instead of two in a
    5x5 square.  Within each block of ``period`` letters the three coordinate
    rows are written out one after another and re-read in threes, so every
    output letter depends on three input letters rather than two -- the
    strongest fractionation in this collection.

    The attack is the same shape as Bifid's, and so are its limits: the period
    and the 27-cell cube have to be recovered together, which is a hill climb
    per period, and it is marked experimental for the same honest reason.
    """

    info = CipherInfo(
        name="trifid",
        title="Trifid",
        family=Family.POLYGRAPHIC,
        key_type="keyword + period",
        keyspace=None,
        deterministic=False,
        min_length=90,
        cost=BRUTAL,
        alphabet=A27,
        aliases=("trifid_cipher", "delastelle"),
        description="Three coordinates per letter in a 3x3x3 cube, recombined within a period. Experimental solver.",
        example_key={"key": "TRIFID", "period": 5},
    )
    max_period = 12

    def prepare(self, text: str) -> str:
        """Keep the cube's alphabet, full stop included.

        The filler is a real symbol of this cipher: the cube has 27 cells and
        a 26-letter message will produce ``.`` in the ciphertext whenever the
        fractionation lands there.  Stripping it -- which a letters-only
        prepare does -- silently deletes a character and every block after it
        decrypts one position out.
        """
        return "".join(c for c in text.upper() if c in A27)

    def _params(self, key: Any) -> tuple[str, int]:
        if isinstance(key, dict):
            return make_grid(str(key.get("key", "")), A27), int(key.get("period", 5))
        if isinstance(key, (tuple, list)):
            return make_grid(str(key[0]), A27), int(key[1])
        return make_grid(str(key), A27), 5

    def encrypt(self, plaintext: str, key: Any = None) -> str:
        cube, period = self._params(key or self.info.example_key)
        stream = self.prepare(plaintext)
        pos = {ch: i for i, ch in enumerate(cube)}
        out: list[str] = []
        for start in range(0, len(stream), period):
            block = stream[start : start + period]
            triples = [divmod(pos.get(c, 0), 9) for c in block]
            layers = [t[0] for t in triples]
            rows = [divmod(t[1], 3)[0] for t in triples]
            cols = [t[1] % 3 for t in triples]
            digits = layers + rows + cols
            for i in range(0, len(digits) - 2, 3):
                out.append(cube[digits[i] * 9 + digits[i + 1] * 3 + digits[i + 2]])
        return "".join(out)

    def decrypt(self, ciphertext: str, key: Any = None) -> str:
        cube, period = self._params(key or self.info.example_key)
        return self._decrypt_cube(self.prepare(ciphertext), cube, period)

    def _decrypt_cube(self, stream: str, cube: str, period: int) -> str:
        """Decrypt against an already-built cube (the hill climber's entry point)."""
        pos = {ch: i for i, ch in enumerate(cube)}
        out: list[str] = []
        for start in range(0, len(stream), period):
            block = stream[start : start + period]
            digits: list[int] = []
            for ch in block:
                layer, rest = divmod(pos.get(ch, 0), 9)
                digits.extend((layer, rest // 3, rest % 3))
            third = len(digits) // 3
            layers = digits[:third]
            rows = digits[third : 2 * third]
            cols = digits[2 * third :]
            for i in range(third):
                out.append(cube[layers[i] * 9 + rows[i] * 3 + cols[i]])
        return "".join(out)

    def crack(self, ciphertext: str, ctx: CrackContext) -> Iterator[Candidate]:
        stream = self.prepare(ciphertext)
        if len(stream) < self.info.min_length:
            return
        hint = ctx.hints.get("key")
        hint_period = ctx.hints.get("period")
        if isinstance(hint, dict):
            hint_period = hint.get("period", hint_period)
            hint = hint.get("key") or hint.get("cube")
        if hint:
            text = str(hint)
            cube = text if len(set(text)) == 27 else make_grid(text, A27)
            periods = [int(hint_period)] if hint_period else list(range(2, self.max_period + 1))
            for period in periods:
                yield ctx.candidate(
                    self.name,
                    self._decrypt_cube(stream, cube, period),
                    {"key": cube, "period": period},
                    steps=ctx.steps,
                    columns=27,
                    period=period,
                    method="hint",
                )
            return

        results: list[Candidate] = []
        for period in range(2, self.max_period + 1):
            if ctx.expired() or ctx.remaining() < 1.5:
                break
            if len(stream) < period * 9:
                continue
            payloads = [
                (
                    stream,
                    6 if len(stream) < 300 else 3,
                    (ctx.hints.get("seed", 11) + i * 31 + period) % (2**31 - 1),
                    period,
                    2000,
                    ctx.model.language,
                )
                for i in range(max(1, min(ctx.workers, 2)))
            ]
            found = [f for f in parallel_restarts(_trifid_worker, payloads, len(payloads), ctx.deadline) if f]
            if not found:
                continue
            found.sort(key=lambda f: -f[1])
            cube = found[0][0]
            results.append(
                ctx.candidate(
                    self.name,
                    self._decrypt_cube(stream, cube, period),
                    {"key": cube, "period": period},
                    steps=ctx.steps,
                    columns=27,
                    period=period,
                    method="cube hill climbing per period (experimental)",
                )
            )
        results.sort(key=Candidate.sort_key)
        yield from results

    def likelihood(self, text: str, ctx: CrackContext) -> float:
        stream = self.prepare(text)
        if len(stream) < 80:
            return 0.0
        ic = index_of_coincidence(stream)
        ic_fit = max(0.0, min(1.0, (0.062 - ic) / (0.062 - 0.038)))
        fit = ctx.model.ngram_score(stream)
        unreadable = max(0.0, min(1.0, (-5.0 - fit) / 2.0))
        return round(0.45 * ic_fit * unreadable, 4)


def _trifid_worker(payload: tuple) -> tuple:
    stream, restarts, seed, period, max_evals, language = payload
    model = get_model(language)
    rng = random.Random(seed)
    trifid = Trifid()
    cube, _plain, fit, conf, _evals, _used = restart_search(
        stream,
        fitness=model.search_fitness,
        confidence=lambda t: model.score(t).confidence,
        apply_key=lambda text, key: trifid._decrypt_cube(text, "".join(key), period),
        restarts=restarts,
        rng=rng,
        alphabet=A27,
        max_evals=max_evals,
    )
    return "".join(cube), conf, fit
