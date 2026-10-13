"""The self-rotating alphabet (Chaocipher-style) cipher.

Two mixed alphabets, one under the other.  To encipher a letter: find it in
the *top* row, write down the bottom-row letter underneath it, then rotate the
bottom row so that the letter just written sits at the front.  Repeat.  The
bottom row is therefore a necklace that walks one step per plaintext letter::

    c_k = B[ (s0 + sum_{j<=k} t_j) mod 26 ]        t_j = position of p_j in T

with ``T`` the top (substitution) alphabet and ``B`` the bottom necklace.
Two arbitrary permutations is ``26! * 26!`` keys -- the ~176 bits the author
advertises -- and a rotation of ``B`` is the same necklace read further along,
so a recovered key is one representative of a class of equivalents that all
decrypt correctly.

Cryptanalysis
-------------
Writing ``alpha = B^-1`` the definition collapses to a much simpler statement --
one that makes this cipher a member of the *running-sum* family rather than a
"rotor machine" with hidden state::

    alpha(c_k) = alpha(c_{k-1}) + t_k
    =>  p_k = T[ alpha(c_k) - alpha(c_{k-1}) ]

The ciphertext letter is just the running total of the plaintext's top-row
indices, relabelled through the necklace; the plaintext is a plain
*substitution* of the differences of adjacent ciphertext letters.  Three
consequences drive the attacks here:

* **Known plaintext is fatal.**  For any ``i < j`` with ``c_i == c_j`` the
  interval sum ``sum_{i<t<=j} T(p_t)`` is 0 mod 26.  Those are linear equations
  in the 26 unknown T-values: solve them over Z_26 (CRT of Z_2 and Z_13 -- both
  cheap to eliminate in), keep the solutions where T and alpha are bijections,
  and the key falls out.  A few hundred letters of crib is plenty; this is the
  classical Chaocipher result (Byrne's machine was only ever read under known
  plaintext) in an even easier form, because here the necklace state is
  recoverable instead of scrambling itself further.

* **Ciphertext-only is a hidden-permutation problem.**  With only the
  ciphertext there is no letter-level leak at all: the counts are flat by
  construction.  What can be measured is the *transition* structure -- the
  matrix of pairs at any fixed skip is a permuted circulant, so the histogram
  of ``alpha(c_{k+s}) - alpha(c_k)`` is concentrated once ``alpha`` is right,
  and that histogram is the search objective.  This module climbs it with
  exact incremental deltas (one swap changes only the 26 bins touching the two
  letters), starting from the phase seeds that power iteration on the pair
  matrix hands out, and then profiles the remaining *substitution* out of the
  result by bigram hill-climbing.  Both objectives are invariant under
  ``alpha -> u * alpha`` for a unit ``u`` mod 26 and under reflection, so the
  search returns an equivalence class and the 24 transforms are tried against
  the language model to pick the representative that reads as text.

* **Short ciphertexts are safe.**  At a few hundred letters the circulant
  signal sits inside the sampling noise -- which is what makes the 409-letter
  challenge text unsolved here -- so the statistical stage only runs once the
  message is long enough for it to mean anything (:data:`STAT_MIN_LENGTH`).
  Measured on two cores inside the slice the engine actually hands the attack:
  two runs in three at 4000 letters and every run at 7000 up.  The first plaintext letter is not
  recoverable ciphertext-only in any case -- it is the necklace's start offset --
  so a perfect solve reads one letter short at the front.

Alphabet: A-Z.  Key format: ``"TOP|BOTTOM"``, two permutations of A-Z.
"""

from __future__ import annotations

import math
import random
import time
from collections import defaultdict
from itertools import permutations, product
from typing import Any, Iterator

from ..results import Candidate
from ..search import parallel_restarts
from ..text import A26, index_of_coincidence, letters_only
from .base import EXPENSIVE, Cipher, CipherInfo, CrackContext, Family

#: Default key: natural top row, reversed bottom.  This is the author's own
#: worked example, which encrypts ``THAT`` to ``GZZG``.
DEFAULT_KEY = "ABCDEFGHIJKLMNOPQRSTUVWXYZ|ZYXWVUTSRQPONMLKJIHGFEDCBA"

#: Below this many letters the circulant fit is inside the noise and the
#: statistical stage is skipped; short messages need a crib instead.
STAT_MIN_LENGTH = 1200

#: Skip distances pooled into the search statistic.  Pairs at every skip are
#: permuted circulants sharing one permutation, so pooling is free data.
SKIP_DEPTH = 3

#: Units mod 26: the symmetry group of the pairwise objective, plus reflection.
_UNITS = (1, 3, 5, 7, 9, 11, 15, 17, 19, 21, 23, 25)

#: N-gram fitness at which a reading grades as language and the sweep can stop
#: (same convention as the keyed ciphers: English prose runs about -4.3).
_SOLVED_FITNESS = -4.6

#: Letter frequencies, for seeding the substitution fit.
_ENGLISH = (
    8.167, 1.492, 2.782, 4.253, 12.702, 2.228, 2.015, 6.094, 6.966, 0.153,
    0.772, 4.025, 2.406, 6.749, 7.507, 1.929, 0.095, 5.987, 6.327, 9.056,
    2.758, 0.978, 2.360, 0.150, 1.974, 0.074,
)


def parse_key(key: Any) -> tuple[str, str]:
    """Accept ``"TOP|BOTTOM"``, ``"TOP,BOTTOM"``, 52 letters or a 2-sequence."""
    if key is None:
        top, bottom = DEFAULT_KEY.split("|")
    elif isinstance(key, str):
        if "|" in key or "," in key:
            separator = "|" if "|" in key else ","
            left, right = key.split(separator, 1)
            top, bottom = letters_only(left, A26), letters_only(right, A26)
        else:
            text = letters_only(key, A26)
            if len(text) != 52:
                raise ValueError("rotating key must be 'TOP|BOTTOM' (52 letters)")
            top, bottom = text[:26], text[26:]
    else:
        top, bottom = (letters_only(str(x), A26) for x in key[:2])
    if sorted(top) != list(A26) or sorted(bottom) != list(A26):
        raise ValueError("both key rows must be permutations of A-Z")
    return top, bottom


def random_key(rng: random.Random | None = None) -> str:
    """A uniformly random key, mostly for tests and benchmarks."""
    rng = rng or random.Random()
    top, bottom = list(A26), list(A26)
    rng.shuffle(top)
    rng.shuffle(bottom)
    return f"{''.join(top)}|{''.join(bottom)}"


class RotatingAlphabet(Cipher):
    """Self-rotating alphabet ('Chaocipher-style'): a moving necklace."""

    info = CipherInfo(
        name="rotating",
        title="Rotating Alphabet (Chaocipher-style)",
        family=Family.WHEEL,
        keyed=True,
        key_type="TOP|BOTTOM",
        keyspace=None,  # (26! * 26!) / 26 -- not enumerable
        deterministic=False,
        min_length=32,
        # EXPENSIVE, not BRUTAL: the class is the engine's scheduling knob, and
        # this cipher behaves like sum-clock -- instant when a crib is supplied,
        # a real search otherwise.  BRUTAL is scheduled after everything else,
        # by which point a few-second slice is all that is left, and a
        # ciphertext-only solve needs fifteen seconds and a few thousand letters.
        cost=EXPENSIVE,
        hints=("crib", "known", "key"),
        aliases=("rotating", "rotating_alphabet", "rotating-alphabet", "chaocipher"),
        description=(
            "Two mixed alphabets; each letter is read from the bottom row, which "
            "then rotates so the emitted letter leads. Equivalent to a substituted "
            "running sum: a crib breaks it outright in about a second, and without "
            "one it takes a search over several thousand letters."
        ),
        example_key=DEFAULT_KEY,
    )

    # -- the cipher ---------------------------------------------------------- #

    def encrypt(self, plaintext: str, key: Any = None) -> str:
        """Letters are enciphered; anything else passes through, layout intact."""
        top, bottom = parse_key(key)
        pos_top = {c: i for i, c in enumerate(top)}
        out: list[str] = []
        shift = 0
        for ch in plaintext:
            letter = ch.upper()
            if letter not in pos_top:
                out.append(ch)
                continue
            t = pos_top[letter]
            out.append(bottom[(shift + t) % 26])
            shift = (shift + t) % 26
        return "".join(out)

    def decrypt(self, ciphertext: str, key: Any = None) -> str:
        top, bottom = parse_key(key)
        pos_bottom = {c: i for i, c in enumerate(bottom)}
        out: list[str] = []
        shift = 0
        for ch in ciphertext:
            letter = ch.upper()
            if letter not in pos_bottom:
                out.append(ch)
                continue
            idx = pos_bottom[letter]
            out.append(top[(idx - shift) % 26])
            shift = idx
        return "".join(out)

    # -- self-assessment ----------------------------------------------------- #

    def likelihood(self, text: str, ctx: CrackContext) -> float:
        """Flat letters *and* English-shaped differences: the running-sum signature.

        A substitution leaves the letter distribution peaked; a polyalphabetic
        cipher flattens both the letters and their differences.  A running sum
        over a substitution -- this cipher's family -- flattens the letters while
        keeping the difference sequence a *relabelled copy of the plaintext*, so
        its differences are as lopsided as English's letters.  The control is a
        shuffle of the same text, which keeps the letter counts and destroys
        the walk, so the test calibrates itself against the text's own noise.

        It is corroboration, not proof: a Vigenere with a short repeating key
        leaves periodic structure in the differences too (measured 0.58 against
        0.85 here), and the hook only ever orders attacks -- the reading itself
        is what decides.
        """
        stream = self.prepare(text)
        if len(stream) < 300:
            return 0.0
        sample = stream[:6000]
        if index_of_coincidence(sample) > 0.048:
            return 0.0  # too peaked to be walking a necklace
        sigmas = _difference_walk_z(sample)
        if sigmas <= 2.0:
            return 0.0  # inside the noise of a 26-cell chi-square
        # Measured on 5256-letter samples: this cipher 38, a Vigenere with a
        # short key 9, M-94 8, a 20-letter Vigenere 4, everything else below 2.
        score = min(0.85, 0.85 * (1.0 - math.exp(-(sigmas - 2.0) / 6.0)))
        return score * min(1.0, (len(stream) - 300) / 700.0)

    # -- structured seeds ---------------------------------------------------- #

    def _structured_keys(self) -> Iterator[str]:
        yield DEFAULT_KEY
        yield f"{A26}|{A26}"
        for word in ("CIPHER", "BUTTCRACK", "CHAOCIPHER", "ALPHABET", "ROTATING"):
            order: list[str] = []
            for ch in word:
                if ch not in order:
                    order.append(ch)
            order += [ch for ch in A26 if ch not in order]
            yield f"{A26}|{''.join(order)}"
            yield f"{''.join(order)}|{A26}"

    # -- attacks ------------------------------------------------------------- #

    def crack(self, ciphertext: str, ctx: CrackContext) -> Iterator[Candidate]:
        stream = self.prepare(ciphertext)
        if len(stream) < self.info.min_length and not ctx.exhaustive:
            return

        hinted = ctx.hints.get("key")
        if hinted is not None:
            yield self.candidate(
                stream, self.decrypt(stream, hinted), hinted, ctx,
                method="hinted key",
            )
            return

        crib = ctx.hints.get("crib") or ctx.hints.get("known")
        if crib:
            yield from self._crack_known(stream, self.prepare(str(crib)), ctx)
            return

        for key in self._structured_keys():
            plain = self.decrypt(stream, key)
            yield self.candidate(
                stream, plain, key, ctx,
                method="structured key",
                note=(
                    "natural, reversed or keyword-seeded rows -- this only wins "
                    "when the sender used a lazy key"
                ),
            )

        if len(stream) >= STAT_MIN_LENGTH:
            yield from self._crack_statistical(stream, ctx)

    # -- crib attack: linear algebra over Z_26 ------------------------------- #

    def _crack_known(
        self, stream: str, known: str, ctx: CrackContext
    ) -> Iterator[Candidate]:
        """Known plaintext anywhere in the message.

        The equations only care about equal ciphertext letters *inside* the
        crib's span, so a crib can sit at any offset; the sweep tries offset 0
        first and stops as soon as a reading grades as language.  What comes out
        is exact -- the interval sums leave the whole key determined -- so a
        crib of a few hundred letters is game over for the cipher.
        """
        if len(known) < 60 or len(known) > len(stream):
            return
        best: list[Candidate] = []
        for offset in range(len(stream) - len(known) + 1):
            if offset and ctx.expired():
                break
            span = stream[offset : offset + len(known)]
            found = list(self._solve_known(span, known, stream, offset, ctx))
            if found and found[0].fitness >= _SOLVED_FITNESS:
                yield found[0]
                return
            best.extend(found)
            best.sort(key=lambda candidate: -candidate.fitness)
            del best[3:]
        for candidate in best:
            yield candidate

    def _solve_known(
        self, span: str, known: str, stream: str, offset: int, ctx: CrackContext
    ) -> Iterator[Candidate]:
        occurrences: dict[str, list[int]] = defaultdict(list)
        for i, ch in enumerate(span):
            occurrences[ch].append(i)
        letters = sorted(set(known))
        column = {ch: i for i, ch in enumerate(letters)}
        rows: list[list[int]] = []
        for positions in occurrences.values():
            for i, j in zip(positions, positions[1:]):
                counts = [0] * len(letters)
                for k in range(i + 1, j + 1):
                    counts[column[known[k]]] += 1
                rows.append(counts)
        if not rows:
            return

        basis13 = _nullspace_mod(rows, 13)
        basis2 = _nullspace_mod(rows, 2)
        combos = 13 ** len(basis13) * 2 ** len(basis2)
        if combos > 4096:
            return  # a crib this thin leaves more freedom than there is budget
        seen: set[tuple[int, ...]] = set()
        for combo13 in product(range(13), repeat=len(basis13)):
            vec13 = [0] * len(letters)
            for coefficient, basis in zip(combo13, basis13):
                vec13 = [(x + coefficient * y) % 13 for x, y in zip(vec13, basis)]
            for combo2 in product(range(2), repeat=len(basis2)):
                vec2 = [0] * len(letters)
                for coefficient, basis in zip(combo2, basis2):
                    vec2 = [(x + coefficient * y) % 2 for x, y in zip(vec2, basis)]
                tau = [_crt(x, y) for x, y in zip(vec2, vec13)]
                if len(set(tau)) != len(tau) or tuple(tau) in seen:
                    continue
                seen.add(tuple(tau))
                if ctx.expired():
                    return
                yield from self._finish_known(
                    span, known, letters, tau, stream, offset, ctx
                )

    def _finish_known(
        self, span: str, known: str, letters: list[str], tau: list[int],
        stream: str, offset: int, ctx: CrackContext,
    ) -> Iterator[Candidate]:
        """Turn a T-candidate into a decryption: complete it, decrypt, rank.

        Whatever the crib does not cover is enumerated -- there are at most a few
        spare values either side -- and the reading is chosen by the language
        model.  That is what makes the ambiguity harmless: a completion that
        misplaces a key row shows up as gibberish in the message.
        """
        tval = dict(zip(letters, tau))
        alpha: dict[str, int] = {}
        acc = 0
        first: tuple[str, int] | None = None
        for index, (ch, plain_char) in enumerate(zip(span, known)):
            acc = (acc + tval[plain_char]) % 26
            if index == 0:
                first = (ch, acc)
                continue
            if ch in alpha:
                if alpha[ch] != acc:
                    return
            else:
                alpha[ch] = acc
        used = set(alpha.values())
        if len(used) != len(alpha):
            return

        missing_letters = [ch for ch in A26 if ch not in alpha]
        if first is not None and first[0] not in alpha:
            missing_letters.append(first[0])
        missing_plain = [ch for ch in A26 if ch not in tval]
        if len(missing_letters) > 5 or len(missing_plain) > 5:
            return
        if _factorial(len(missing_letters)) * _factorial(len(missing_plain)) > 2048:
            return

        spare_positions = [v for v in range(26) if v not in used]
        spare_values = [v for v in range(26) if v not in set(tau)]
        tail = stream[offset:]
        probe = tail[:800]

        ranked: list[tuple[float, str]] = []
        plain_options = permutations(spare_values) if missing_plain else [()]
        position_options = permutations(spare_positions) if missing_letters else [()]
        position_options = list(position_options)
        for plain_completion in plain_options:
            top_row = _top_row(letters, missing_plain, tau + list(plain_completion))
            for position_completion in position_options:
                if ctx.expired():
                    break
                bottom = _bottom_row_with(alpha, missing_letters, position_completion)
                key = f"{top_row}|{bottom}"
                value = ctx.model.search_fitness(self.decrypt(probe, key))
                ranked.append((value, key))
        if not ranked:
            return
        ranked.sort(key=lambda t: -t[0])

        emitted = 0
        for _, key in ranked[:3]:
            plain = self.decrypt(tail, key)
            yield self.candidate(
                stream, plain, key, ctx,
                method="known plaintext (linear solve mod 26)",
                crib=len(known),
                offset=offset,
                note=(
                    "interval-sum equations between equal ciphertext letters; "
                    "exact once the crib pins the rows"
                ),
            )
            emitted += 1
            if emitted >= 3:
                return

    # -- ciphertext-only: circulant fit + profiled substitution -------------- #

    def _polish(self, stream: str, key: str, ctx: CrackContext, passes: int = 4) -> str:
        """Repair the top row: the necklace is exact, the substitution may not be.

        Swapping two letters of T swaps exactly those two letters in the
        decryption, so each candidate is one ``str.translate`` plus one model
        score -- cheap enough to hill-climb the last few letters on the *whole*
        message, with the same quadgram model the candidates are ranked by.
        """
        top, bottom = parse_key(key)
        plain = self.decrypt(stream, key)
        best = ctx.model.ngram_score(plain, normalise=False)
        for _ in range(passes):
            improved = False
            for x in range(26):
                for y in range(x + 1, 26):
                    a, b = top[x], top[y]
                    swapped = plain.translate(str.maketrans({a: b, b: a}))
                    value = ctx.model.ngram_score(swapped, normalise=False)
                    if value > best:
                        best, plain, improved = value, swapped, True
                        top = top[:x] + b + top[x + 1 : y] + a + top[y + 1 :]
                        break
                if improved:
                    break
            if not improved:
                break
        return f"{top}|{bottom}"

    @staticmethod
    def _sharp(ctx: CrackContext, plain: str) -> float:
        """Mean quadgram per letter -- the ranking objective for finalists.

        ``model.search_fitness`` is built for hill climbing: it is clamped and
        saturates, so a reading with one wrong letter scores *identically* to
        the truth.  Candidates are ranked with the plain model score instead,
        which separates the two by ~10 nats over 4000 letters and so lets the
        last polish pass show up in the order.
        """
        return ctx.model.ngram_score(plain, normalise=False)

    def _crack_statistical(
        self, stream: str, ctx: CrackContext
    ) -> Iterator[Candidate]:
        """Ciphertext-only, two objectives: search cheap, verify sharp.

        The circulant statistic is flat enough that near-mine local optima sit
        within a fraction of a nat of the truth, so the climbs are used to
        *propose* necklaces and the language model is used to *choose*: the
        differences of a right necklace are the plaintext's indices, which makes
        the plaintext a substitution of them, and the best such substitution
        separates the truth from every impostor by ~2 nats per letter.
        """
        work = stream[:9000]  # the statistic saturates; keep the climbs cheap
        # The engine hands a BRUTAL attack a ~20 s slice, so the split matters:
        # the workers search the cheap statistic (one batch, so the answer comes
        # back with time to spare) and the sharp objective, which only this
        # process can afford, gets everything they did not spend.
        slice_seconds = max(3.0, min(30.0, ctx.remaining() * 0.55))
        payloads = [
            (work, seed, slice_seconds, SKIP_DEPTH)
            for seed in range(max(2, ctx.workers))
        ]
        results = parallel_restarts(_rotating_worker, payloads, ctx.workers, ctx.deadline)

        ordered, symmetric = _pair_counts(work, SKIP_DEPTH)
        bigram = _bigram_log_table(ctx.model)
        sequence = [ord(ch) - 65 for ch in work[:1500]]

        ranked: list[tuple[float, tuple[int, ...]]] = []
        for entry in results or []:
            for score, alpha in entry:
                ranked.append((score, tuple(alpha)))
        ranked.sort(key=lambda t: -t[0])

        candidates: list[list[int]] = []
        seen: set[tuple[int, ...]] = set()
        for _, alpha in ranked:
            if alpha in seen:
                continue
            seen.add(alpha)
            candidates.append(list(alpha))
        # The tournament ranking costs microseconds and often starts within a
        # couple of swaps of the truth, so it always gets a seat at the table.
        for seed in [_tournament_seed(ordered)] + _phase_seeds(ordered):
            if tuple(seed) in seen:
                continue
            seen.add(tuple(seed))
            candidates.append(list(seed))

        refine_deadline = time.time() + max(5.0, ctx.remaining() * 0.55)
        finals: list[tuple[float, list[int]]] = []
        picks = candidates[:14]
        for index, alpha in enumerate(picks):
            now = time.time()
            if index and now > refine_deadline:
                break
            share = max(0.5, (refine_deadline - now) / (len(picks) - index))
            stop = min(refine_deadline, now + share)
            alpha = _climb_alpha(symmetric, alpha, stop)[1]
            score, alpha, _ = _climb_text(sequence, alpha, bigram, stop)
            # A couple of kicks around the best reading of *this* candidate: the
            # profiled score is expensive per evaluation, so the iterated search
            # is only worth it while the candidate is already close.
            kicks = random.Random(index)
            for _ in range(6):
                if time.time() > stop:
                    break
                probe = list(alpha)
                for _ in range(1 + kicks.randrange(3)):
                    x, y = kicks.randrange(26), kicks.randrange(26)
                    probe[x], probe[y] = probe[y], probe[x]
                value, probe_alpha, _ = _climb_text(sequence, probe, bigram, stop, sweeps=2)
                if value > score:
                    score, alpha = value, probe_alpha
                else:
                    break
            finals.append((score, alpha))
        if not finals:
            return
        finals.sort(key=lambda t: -t[0])

        fits: list[tuple[float, str]] = []
        for _, alpha in finals[:5]:
            differences = _differences(stream, dict(enumerate(alpha)))
            pairs = _difference_pair_counts(differences)
            readings: list[tuple[float, list[int], int]] = []
            for unit in _UNITS:
                for sign in (1, -1):
                    scale = (sign * unit) % 26
                    table = _scale_counts(pairs, scale)
                    tau, _ = _fit_substitution(table, bigram, sweeps=4)
                    scaled = [(scale * d) % 26 for d in differences]
                    plain = "".join(A26[tau[d]] for d in scaled)
                    readings.append((self._sharp(ctx, plain), tau, scale))
            readings.sort(key=lambda t: -t[0])
            for _, tau, scale in readings[:4]:
                # The necklace comes from the search's own alpha, rescaled by the
                # transform -- not from the guessed text, which would demand a
                # flawless substitution fit before the key could be assembled.
                gamma = {chr(65 + i): (scale * alpha[i]) % 26 for i in range(26)}
                key = f"{_tau_row(tau)}|{_bottom_row(gamma)}"
                plain = self.decrypt(stream, key)
                fits.append((self._sharp(ctx, plain), key))
        # Repairing the top rows is one translate plus one score each, so every
        # serious candidate gets it before the ranking is final.
        polished = []
        for _, key in fits[:8]:
            repaired = self._polish(stream, key, ctx, passes=6)
            plain = self.decrypt(stream, repaired)
            polished.append((self._sharp(ctx, plain), repaired))
        polished.extend(fits)
        polished.sort(key=lambda t: -t[0])

        seen_keys: set[str] = set()
        for _, key in polished:
            if key in seen_keys:
                continue
            seen_keys.add(key)
            yield self.candidate(
                stream, self.decrypt(stream, key), key, ctx,
                method="ciphertext-only (circulant fit + substitution profile)",
                note=(
                    "statistical attack: needs a long message; a few hundred "
                    "letters sit inside the noise floor and need a crib instead"
                ),
            )
            if len(seen_keys) >= 3:
                return


# --------------------------------------------------------------------------- #
# text utilities
# --------------------------------------------------------------------------- #

def _differences(stream: str, alpha: dict[int, int]) -> list[int]:
    """``alpha(c_k) - alpha(c_{k-1})`` for k = 1.. -- the plaintext's indices.

    ``alpha`` is indexed by ciphertext letter *number* (0-25), which is what the
    necklace search works with; the plaintext value at k comes out one step late
    because the first ciphertext letter only fixes the unknown start offset.
    """
    idx = [ord(ch) - 65 for ch in stream]
    return [(alpha[idx[k]] - alpha[idx[k - 1]]) % 26 for k in range(1, len(idx))]


def _difference_walk_chi(stream: str) -> float:
    """Chi-square of the consecutive-difference histogram against a flat one.

    The signature of a running sum is that it hides the plaintext's letters in
    the *differences* of its own letters: ``c[k+1] - c[k]`` is a relabelled
    plaintext letter, so the difference values are as lopsided as English's
    letter histogram even though the ciphertext's own letters are flat.  The
    statistic is computed on the difference *values*, so it does not depend on
    which ciphertext letter carries which index -- the relabelling the attack
    has to find is invisible here, and the caller supplies the reference by
    measuring a shuffle of the same text.
    """
    index = [ord(ch) - 65 for ch in stream]
    if len(index) < 2:
        return 0.0
    counts = [0] * 26
    for k in range(len(index) - 1):
        counts[(index[k + 1] - index[k]) % 26] += 1
    n = len(index) - 1
    expected = n / 26.0
    return sum((count - expected) ** 2 for count in counts) / expected


def _difference_walk_z(sample: str) -> float:
    """How far the difference histogram out-peaks the text's own shuffle.

    A chi-square with 26 cells has a standard deviation of ``sqrt(2 * 26)``,
    and the excess over the control is a difference of two such statistics, so
    dividing by ``sqrt(4 * 26)`` turns the excess into roughly "sigmas".  The
    control is a shuffle of the same letters -- the same counts, no walk -- so
    the measurement carries its own noise floor and needs no tuned constant.
    The two histograms are not independent, which makes the scale a little
    conservative, and that is the safe direction for a hook that only orders
    attacks.
    """
    control = list(sample)
    random.Random(0).shuffle(control)
    excess = _difference_walk_chi(sample) - _difference_walk_chi("".join(control))
    return excess / math.sqrt(4.0 * 26.0)


def _pair_counts(stream: str, skips: int = SKIP_DEPTH):
    """Ordered pair counts ``P[a][b]`` and symmetric weights ``U[a][b]``."""
    idx = [ord(ch) - 65 for ch in stream]
    ordered = [[0] * 26 for _ in range(26)]
    for skip in range(1, skips + 1):
        for i in range(len(idx) - skip):
            ordered[idx[i]][idx[i + skip]] += 1
    symmetric = [[0] * 26 for _ in range(26)]
    for a in range(26):
        for b in range(26):
            symmetric[a][b] = (
                ordered[a][a] if a == b else ordered[a][b] + ordered[b][a]
            )
    return ordered, symmetric


def _bins(symmetric: list[list[int]], alpha: list[int]) -> list[int]:
    """Histogram of ``alpha(b) - alpha(a)`` weighted by the symmetric pair counts."""
    weights = [0] * 26
    for a in range(26):
        weights[0] += symmetric[a][a]
        row = symmetric[a]
        for b in range(a + 1, 26):
            weight = row[b]
            if weight:
                d = (alpha[b] - alpha[a]) % 26
                weights[d] += weight
                weights[-d % 26] += weight
    return weights


def _concentration(weights: list[int]) -> float:
    return sum(w * math.log(w) for w in weights if w)


def _swap_changes(
    symmetric: list[list[int]], alpha: list[int], x: int, y: int
) -> dict[int, int]:
    """Exact change in every affected bin when ``alpha[x]`` and ``alpha[y]`` swap.

    Only the pairs touching ``x`` or ``y`` move, and the pair ``{x, y}`` lands on
    the same two bins either way, so this is 26 arithmetic steps rather than a
    full re-histogram: the whole climb stays linear in the number of swaps.
    """
    changes: dict[int, int] = {}
    for c in range(26):
        if c == x or c == y:
            continue
        wx, wy = symmetric[x][c], symmetric[y][c]
        if wx:
            d = (alpha[c] - alpha[x]) % 26
            changes[d] = changes.get(d, 0) - wx
            changes[-d % 26] = changes.get(-d % 26, 0) - wx
            d = (alpha[c] - alpha[y]) % 26
            changes[d] = changes.get(d, 0) + wx
            changes[-d % 26] = changes.get(-d % 26, 0) + wx
        if wy:
            d = (alpha[c] - alpha[y]) % 26
            changes[d] = changes.get(d, 0) - wy
            changes[-d % 26] = changes.get(-d % 26, 0) - wy
            d = (alpha[c] - alpha[x]) % 26
            changes[d] = changes.get(d, 0) + wy
            changes[-d % 26] = changes.get(-d % 26, 0) + wy
    return changes


def _climb_alpha(
    symmetric: list[list[int]], alpha: list[int], deadline: float,
    max_sweeps: int = 40,
) -> tuple[float, list[int]]:
    """Coordinate ascent on the pooled-difference concentration."""
    weights = _bins(symmetric, alpha)
    current = _concentration(weights)
    for _ in range(max_sweeps):
        improved = False
        for x in range(26):
            for y in range(x + 1, 26):
                if time.time() > deadline:
                    return current, alpha
                changes = _swap_changes(symmetric, alpha, x, y)
                delta = 0.0
                for bin_index, change in changes.items():
                    if not change:
                        continue
                    before = weights[bin_index]
                    after = before + change
                    delta += _bin_value(after) - _bin_value(before)
                if delta > 0:
                    for bin_index, change in changes.items():
                        weights[bin_index] += change
                    alpha[x], alpha[y] = alpha[y], alpha[x]
                    current += delta
                    improved = True
        if not improved:
            break
    return current, alpha


def _bin_value(weight: int) -> float:
    return weight * math.log(weight) if weight > 0 else 0.0


def _transpose(matrix: list[list[int]]) -> list[list[int]]:
    return [[matrix[b][a] for b in range(26)] for a in range(26)]


def _phase_seeds(
    ordered: list[list[int]], directions: int = 3, iterations: int = 40
) -> list[list[int]]:
    """Recover ``alpha`` from the phases of the pair matrix's eigenvectors.

    Every skip matrix is a permuted circulant, ``P = Q C Q^-1``, so its
    eigenvectors are ``v_j[a] = omega**(j * alpha[a])``: the *phases* of an
    eigenvector spell out the permutation we are looking for, one frequency at a
    time.  The dominant eigenvalue of such a matrix is often real, and a real
    eigenvector's phases are 0 and pi -- no information -- so the dominant
    direction is deflated and the iteration is restarted, exposing the complex
    pair underneath.  When this lands it hands back the exact class in
    milliseconds instead of a few thousand climbs; when it does not, the random
    restarts are still there.
    """
    n = 26
    rng = random.Random(0xC1F3)
    matrix = [[complex(ordered[a][b]) for b in range(n)] for a in range(n)]
    seeds: list[list[int]] = []
    for _ in range(directions):
        vector = [complex(rng.random() - 0.5, rng.random() - 0.5) for _ in range(n)]
        for _ in range(iterations):
            nxt = [
                sum(matrix[a][b] * vector[b] for b in range(n)) for a in range(n)
            ]
            norm = math.sqrt(sum(abs(z) ** 2 for z in nxt))
            if norm == 0.0:
                break
            vector = [z / norm for z in nxt]
        product = [
            sum(matrix[a][b] * vector[b] for b in range(n)) for a in range(n)
        ]
        eigenvalue = sum(
            vector[a].conjugate() * product[a] for a in range(n)
        )
        seeds.extend(_phases_of(vector))
        if abs(eigenvalue) < 1e-9:
            break
        # Deflate the direction just found so the next one is not the same.
        for a in range(n):
            row = matrix[a]
            va = vector[a]
            for b in range(n):
                row[b] -= eigenvalue * va * vector[b].conjugate()
    return seeds


def _phases_of(vector: list[complex]) -> list[list[int]]:
    """Frequency-by-frequency permutation guesses from an eigenvector's phases."""
    reference = max(range(26), key=lambda a: abs(vector[a]))
    if abs(vector[reference]) == 0.0:
        return []
    guesses: list[list[int]] = []
    for frequency in range(1, 26):
        guess: list[int] = []
        for a in range(26):
            z = vector[a] / vector[reference]
            theta = math.atan2(z.imag, z.real) % (2.0 * math.pi)
            offset = theta * 26.0 / (2.0 * math.pi * frequency)
            guess.append(int(round(offset)) % 26)
        if len(set(guess)) == 26:
            guesses.append(guess)
    return guesses


def _tournament_seed(ordered: list[list[int]]) -> list[int]:
    """Order the letters by who beats whom in the antisymmetric pair matrix.

    ``D[a][b] = P[a][b] - P[b][a]`` is an *odd* permuted circulant: with
    ``delta = alpha[b] - alpha[a]`` it equals ``g(delta)`` for an odd ``g`` --
    positive when ``b`` sits a few steps ahead of ``a`` in the necklace, negative
    when it trails.  So the matrix is a tournament whose winner list is the
    necklace order: count the wins and rank.  It lands within a couple of
    positions of the truth for free, which is exactly the starting point the
    concentration climb needs to have a chance of finishing.
    """
    wins = [0] * 26
    for a in range(26):
        row = ordered[a]
        score = 0
        for b in range(26):
            if a == b:
                continue
            difference = row[b] - ordered[b][a]
            score += 1 if difference > 0 else (-1 if difference < 0 else 0)
        wins[a] = score
    order = sorted(range(26), key=lambda a: -wins[a])
    seed = [0] * 26
    for rank, letter in enumerate(order):
        seed[letter] = rank
    return seed


def _text_objective(
    sequence: list[int], alpha: list[int], table: list[list[float]], sweeps: int = 2
):
    """Profile the substitution out of a candidate necklace, and score the text.

    The differences ``alpha(c_k) - alpha(c_{k-1})`` are the plaintext's top-row
    indices, so the plaintext is a *substitution* of them: fit the best
    substitution and the resulting bigram score is the language-model reading of
    that necklace.  It is the sharp criterion the concentration statistic can
    only approximate -- measured against noise optima it separates by ~2 nats
    per letter -- and the number of letters it needs is bounded by the sample,
    not by the message.
    """
    counts = [[0] * 26 for _ in range(26)]
    previous = None
    for i in range(1, len(sequence)):
        d = (alpha[sequence[i]] - alpha[sequence[i - 1]]) % 26
        if previous is not None:
            counts[previous][d] += 1
        previous = d
    return _fit_substitution(counts, table, sweeps=sweeps)


def _climb_text(
    sequence: list[int], alpha: list[int], table: list[list[float]],
    deadline: float, sweeps: int = 3,
):
    """Coordinate ascent on the profiled text score: the last few letters.

    The concentration climb stalls when two letters are a hair from right and
    their swap is invisible to an almost-symmetric statistic; the text score
    sees it, because a misplaced letter scrambles every difference it takes part
    in.  This is expensive per evaluation, so it refines candidates rather than
    searching with them.
    """
    tau, score = _text_objective(sequence, alpha, table, sweeps=2)
    for _ in range(sweeps):
        improved = False
        for x in range(26):
            for y in range(x + 1, 26):
                if time.time() > deadline:
                    return score, alpha, tau
                alpha[x], alpha[y] = alpha[y], alpha[x]
                candidate, value = _text_objective(sequence, alpha, table, sweeps=2)
                if value > score:
                    score, tau, improved = value, candidate, True
                else:
                    alpha[x], alpha[y] = alpha[y], alpha[x]
        if not improved:
            break
    return score, alpha, tau


def _rotating_worker(payload: tuple) -> list[tuple[float, list[int]]]:
    """One search process: seeded and random climbs, best few local optima."""
    stream, seed, seconds, skips = payload
    ordered, symmetric = _pair_counts(stream, skips)
    rng = random.Random(seed)
    deadline = time.time() + seconds
    best: list[tuple[float, list[int]]] = []

    def offer(score: float, alpha: list[int]) -> None:
        best.append((score, alpha))
        best.sort(key=lambda t: -t[0])
        del best[12:]

    starts = [_tournament_seed(ordered)]
    starts += _phase_seeds(ordered) + _phase_seeds(_transpose(ordered))
    for start in starts:
        if time.time() > deadline:
            break
        score, alpha = _climb_alpha(symmetric, list(start), deadline)
        offer(score, alpha)

    # Random restarts find the right basin; once one has been found, small
    # perturbations of the best reading are the cheapest way to stay in it.
    while time.time() < deadline:
        if best and rng.random() < 0.5:
            alpha = list(best[rng.randrange(min(4, len(best)))][1])
            for _ in range(1 + rng.randrange(3)):
                x, y = rng.randrange(26), rng.randrange(26)
                alpha[x], alpha[y] = alpha[y], alpha[x]
        else:
            alpha = list(range(26))
            rng.shuffle(alpha)
        # A cap, not a promise: a random start that is still improving after a
        # couple of seconds is rare, and cutting it loose buys many more restarts.
        score, alpha = _climb_alpha(
            symmetric, alpha, min(deadline, time.time() + 2.5), max_sweeps=15
        )
        offer(score, alpha)
    return best


# --------------------------------------------------------------------------- #
# substitution profiling (value labels -> letters)
# --------------------------------------------------------------------------- #

def _bigram_log_table(model) -> list[list[float]]:
    """``L[a][b] = log P(b | a)`` from the model's bigram table."""
    table = model.ngrams.get(2) or {}
    floor = model.ngram_floor(2)
    out = [[floor] * 26 for _ in range(26)]
    for gram, value in table.items():
        if len(gram) == 2 and gram.isalpha():
            out[ord(gram[0].upper()) - 65][ord(gram[1].upper()) - 65] = value
    return out


def _difference_pair_counts(differences: list[int]) -> list[list[int]]:
    """Consecutive pairs of value labels: the plaintext's bigrams, relabelled."""
    counts = [[0] * 26 for _ in range(26)]
    for a, b in zip(differences, differences[1:]):
        counts[a][b] += 1
    return counts


def _scale_counts(counts: list[list[int]], scale: int) -> list[list[int]]:
    """Relabel the value axis by ``d -> scale * d``; a bijection, so just moved."""
    out = [[0] * 26 for _ in range(26)]
    inverse = [0] * 26
    for d in range(26):
        inverse[(scale * d) % 26] = d
    for x in range(26):
        source_x = inverse[x]
        row, target = counts[source_x], out[x]
        for y in range(26):
            target[y] = row[inverse[y]]
    return out


def _sub_score(counts: list[list[int]], table: list[list[float]], tau: list[int]) -> float:
    total = 0.0
    for a in range(26):
        row = counts[a]
        mapped = table[tau[a]]
        for b in range(26):
            if row[b]:
                total += row[b] * mapped[tau[b]]
    return total


def _sub_delta(
    counts: list[list[int]], table: list[list[float]], tau: list[int], x: int, y: int
) -> float:
    """Change in the bigram score from swapping ``tau[x]`` and ``tau[y]``."""
    tx, ty = tau[x], tau[y]
    delta = 0.0
    row_x, row_y = table[tx], table[ty]
    for c in range(26):
        if c == x or c == y:
            continue
        tc = tau[c]
        delta += counts[x][c] * (table[ty][tc] - row_x[tc])
        delta += counts[y][c] * (row_x[tc] - table[ty][tc])
        delta += counts[c][x] * (table[tc][ty] - table[tc][tx])
        delta += counts[c][y] * (table[tc][tx] - table[tc][ty])
    delta += counts[x][x] * (table[ty][ty] - table[tx][tx])
    delta += counts[y][y] * (table[tx][tx] - table[ty][ty])
    delta += counts[x][y] * (table[ty][tx] - table[tx][ty])
    delta += counts[y][x] * (table[tx][ty] - table[ty][tx])
    return delta


def _fit_substitution(
    counts: list[list[int]], table: list[list[float]], sweeps: int = 4
) -> tuple[list[int], float]:
    """Best value-label -> letter map for the given bigram counts."""
    weights = [sum(row) for row in counts]
    order = sorted(range(26), key=lambda v: -weights[v])
    by_frequency = sorted(range(26), key=lambda letter: -_ENGLISH[letter])
    tau = [0] * 26
    for value, letter in zip(order, by_frequency):
        tau[value] = letter
    current = _sub_score(counts, table, tau)
    for _ in range(sweeps):
        improved = False
        for x in range(26):
            for y in range(x + 1, 26):
                delta = _sub_delta(counts, table, tau, x, y)
                if delta > 0:
                    tau[x], tau[y] = tau[y], tau[x]
                    current += delta
                    improved = True
        if not improved:
            break
    return tau, current


def _tau_row(tau: list[int]) -> str:
    """The top row: value label -> letter."""
    row = ["?"] * 26
    for value, letter in enumerate(tau):
        row[value] = A26[letter]
    return "".join(row)


def _top_row(letters: list[str], missing: list[str], fitted: list[int]) -> str:
    """Value label -> letter, from the crib's letters and any completions."""
    row = ["?"] * 26
    for ch, value in zip(list(letters) + list(missing), fitted):
        row[value] = ch
    return "".join(row)


def _bottom_row(alpha: dict[str, int]) -> str:
    row = ["?"] * 26
    for ch, value in alpha.items():
        row[value] = ch
    return "".join(row)


def _bottom_row_with(
    alpha: dict[str, int], missing: list[str], assignment: tuple[int, ...]
) -> str:
    """Complete a partial necklace, then stringify it."""
    row = _bottom_row(alpha)
    chars = list(row)
    for ch, value in zip(missing, assignment):
        chars[value] = ch
    return "".join(chars)


def _factorial(n: int) -> int:
    out = 1
    for value in range(2, n + 1):
        out *= value
    return out


# --------------------------------------------------------------------------- #
# modular linear algebra for the crib attack
# --------------------------------------------------------------------------- #

def _rref_mod(rows: list[list[int]], p: int) -> tuple[list[list[int]], list[int]]:
    matrix = [[x % p for x in row] for row in rows]
    height = len(matrix)
    width = len(matrix[0]) if height else 0
    pivots: list[int] = []
    r = 0
    for c in range(width):
        pivot = None
        for i in range(r, height):
            if matrix[i][c] % p:
                pivot = i
                break
        if pivot is None:
            continue
        matrix[r], matrix[pivot] = matrix[pivot], matrix[r]
        inverse = pow(matrix[r][c], -1, p)
        matrix[r] = [(x * inverse) % p for x in matrix[r]]
        for i in range(height):
            if i != r and matrix[i][c] % p:
                factor = matrix[i][c]
                matrix[i] = [(x - factor * y) % p for x, y in zip(matrix[i], matrix[r])]
        pivots.append(c)
        r += 1
        if r == height:
            break
    return matrix, pivots


def _nullspace_mod(rows: list[list[int]], p: int) -> list[list[int]]:
    """Basis of the (homogeneous) solution space of ``rows`` over Z_p."""
    matrix, pivots = _rref_mod(rows, p)
    width = len(matrix[0]) if matrix else 0
    free = [c for c in range(width) if c not in pivots]
    basis: list[list[int]] = []
    for f in free:
        vec = [0] * width
        vec[f] = 1
        for i, c in enumerate(pivots):
            vec[c] = (-matrix[i][f]) % p
        basis.append(vec)
    return basis


def _crt(bit: int, residue: int) -> int:
    """The value mod 26 with the given parity and residue mod 13."""
    for value in range(26):
        if value % 2 == bit and value % 13 == residue:
            return value
    raise AssertionError("no CRT solution")
