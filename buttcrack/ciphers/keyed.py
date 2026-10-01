"""Periodic ciphers over a *keyed* alphabet: Quagmire III and sum-clocks.

Every cipher in :mod:`~buttcrack.ciphers.polyalphabetic` does its arithmetic in
the ordinary A-Z index space.  A whole family of puzzle ciphers -- the Kryptos
sculpture's own, and the Paradigm Kryptos CTF built on top of it -- does the
same arithmetic in a *keyed* space instead::

    idx_K(c) = (idx_K(p) + idx_K(k)) mod 26        K = "KRYPTOSABCDEFGHIJLMNQUVWXZ"

That one substitution changes nothing about the algebra and everything about
the attack: a Vigenère solver that assumes A=0 recovers garbage, because the
per-column shift it finds is a shift of the *wrong* alphabet.

Two ciphers live here:

``quagmire3``
    A keyword over a keyed alphabet.  Given the alphabet it is Vigenère in
    disguise, so the period comes from the index of coincidence and each column
    falls to chi-squared -- in keyed space.  The alphabet itself is searched
    over a list of candidates, with the Kryptos alphabet first because it is by
    far the most common one in the wild.

``sum_clock``
    Several short wheels added together::

        K[t] = (q_a[t mod a] + q_b[t mod b] + ...) mod 26

    This is the interesting one.  Two wheels of period 10 and 8 give a key of
    period lcm(10, 8) = 80, and four wheels of 4, 5, 6 and 7 give 420 -- longer
    than the message, so column-wise analysis has nothing to work with.  But
    the *unknowns* are only ``a + b + ...`` letters (22 for the four-wheel
    case, and one fewer per wheel after gauge freedom), so the right move is to
    solve the wheels jointly by coordinate ascent rather than to solve columns
    of the expanded key.  See :meth:`SumClock.crack`.
"""

from __future__ import annotations

import random
import time
from collections.abc import Iterator, Sequence
from itertools import combinations
from typing import Any

from ..results import Candidate
from ..text import A26, index_of_coincidence, keyed_alphabet, letters_only
from .base import EXPENSIVE, MODERATE, Cipher, CipherInfo, CrackContext, Family

#: N-gram fitness at which a reading is English and the search can stop.
#: English prose averages about -4.3 per character under the quadgram model.
SOLVED_FITNESS = -4.6

#: The Kryptos sculpture's keyed alphabet: the keyword KRYPTOS followed by the
#: unused letters in order.  Sanborn used it for K1-K3, and the Paradigm
#: Kryptos CTF uses it throughout.
KRYPTOS_ALPHABET = "KRYPTOSABCDEFGHIJLMNQUVWXZ"

#: Alphabets tried, in order, when the key does not name one.  The plain
#: alphabet is included because Quagmire III over A-Z is just Vigenère, and a
#: puzzle that turns out to be plain should be reported as such.
CANDIDATE_ALPHABETS: tuple[tuple[str, str], ...] = (
    ("kryptos", KRYPTOS_ALPHABET),
    ("plain", A26),
    ("palimpsest", keyed_alphabet("PALIMPSEST")),
    ("abscissa", keyed_alphabet("ABSCISSA")),
    ("cipher", keyed_alphabet("CIPHER")),
)


def alphabet_for(name_or_alphabet: str) -> str:
    """Resolve a name, keyword or explicit 26-letter alphabet."""
    text = (name_or_alphabet or "").strip()
    if not text:
        return KRYPTOS_ALPHABET
    upper = text.upper()
    if len(set(upper)) == 26 and set(upper) == set(A26):
        return upper
    for name, alphabet in CANDIDATE_ALPHABETS:
        if text.lower() == name:
            return alphabet
    return keyed_alphabet(upper)


class _KeyedPeriodic(Cipher):
    """Shared machinery: index in a keyed alphabet, add a keystream, index back."""

    #: Letters per key symbol below which a recovered key is not evidence.
    min_letters_per_column = 6

    @staticmethod
    def _index(alphabet: str) -> dict[str, int]:
        return {ch: i for i, ch in enumerate(alphabet)}

    def prepare(self, text: str) -> str:
        return letters_only(text).upper()

    def _transform(self, stream: str, alphabet: str, keystream: Sequence[int], sign: int) -> str:
        index = self._index(alphabet)
        out = []
        for i, ch in enumerate(stream):
            position = index.get(ch)
            if position is None:
                out.append(ch)
                continue
            out.append(alphabet[(position + sign * keystream[i % len(keystream)]) % 26])
        return "".join(out)

    def _columns(self, stream: str, alphabet: str, period: int) -> list[list[int]]:
        """Letter indices of each column, in keyed-alphabet space."""
        index = self._index(alphabet)
        columns: list[list[int]] = [[] for _ in range(period)]
        for i, ch in enumerate(stream):
            position = index.get(ch)
            if position is not None:
                columns[i % period].append(position)
        return columns

    def _solve_column(self, column: Sequence[int], alphabet: str, ctx: CrackContext) -> int:
        """Best shift for one column by chi-squared, in keyed space.

        The reference distribution has to be re-indexed into the keyed
        alphabet: English says ``E`` is common, and ``E`` sits at index 9 of
        the Kryptos alphabet, not 4.
        """
        reference = ctx.model.monogram_reference()
        expected = [reference[ch] for ch in alphabet]
        n = len(column)
        if not n:
            return 0
        counts = [0] * 26
        for value in column:
            counts[value] += 1
        best_shift, best_chi = 0, float("inf")
        for shift in range(26):
            chi = 0.0
            for i in range(26):
                exp = expected[i] * n
                if exp > 0:
                    diff = counts[(i + shift) % 26] - exp
                    chi += diff * diff / exp
            if chi < best_chi:
                best_shift, best_chi = shift, chi
        return best_shift


class Quagmire3(_KeyedPeriodic):
    """Quagmire III: a keyword applied over a keyed alphabet.

    The Kryptos sculpture's K1 and K2 are Quagmire III, and so is most of the
    Paradigm Kryptos CTF.  With the alphabet known it is Vigenère in a
    relabelled space -- period from the index of coincidence, columns from
    chi-squared -- and the whole difficulty is that a solver which assumes A-Z
    never finds it.
    """

    info = CipherInfo(
        name="quagmire3",
        title="Quagmire III (keyed alphabet)",
        family=Family.POLYALPHABETIC,
        key_type="keyword + alphabet",
        keyspace=None,
        min_length=40,
        cost=MODERATE,
        aliases=("quagmire", "quag3", "kryptos", "keyed_vigenere"),
        description="Vigenere over a keyed alphabet (KRYPTOS by default). Period from IC, columns by chi-squared in keyed space.",
        example_key={"key": "PROVENANCE", "alphabet": "kryptos"},
    )
    max_period = 20

    # -- key handling ------------------------------------------------------- #
    def _params(self, key: Any) -> tuple[str, list[int]]:
        """Return ``(alphabet, keystream)``."""
        alphabet = KRYPTOS_ALPHABET
        word = ""
        if isinstance(key, dict):
            alphabet = alphabet_for(str(key.get("alphabet", "kryptos")))
            word = str(key.get("key") or key.get("keyword") or "")
        elif isinstance(key, (tuple, list)) and len(key) >= 2:
            word, alphabet = str(key[0]), alphabet_for(str(key[1]))
        else:
            word = str(key or "")
        index = self._index(alphabet)
        stream = [index[c] for c in letters_only(word).upper() if c in index]
        return alphabet, stream or [0]

    def key_word(self, alphabet: str, shifts: Sequence[int]) -> str:
        return "".join(alphabet[s % 26] for s in shifts)

    # -- transforms --------------------------------------------------------- #
    def encrypt(self, plaintext: str, key: Any = None) -> str:
        alphabet, stream = self._params(key or self.info.example_key)
        return self._transform(self.prepare(plaintext), alphabet, stream, +1)

    def decrypt(self, ciphertext: str, key: Any = None) -> str:
        alphabet, stream = self._params(key or self.info.example_key)
        return self._transform(self.prepare(ciphertext), alphabet, stream, -1)

    # -- cryptanalysis ------------------------------------------------------ #
    def _periods(self, stream: str, ctx: CrackContext) -> list[int]:
        hint = ctx.hints.get("key_length") or ctx.hints.get("period")
        if hint:
            return [int(hint)]
        # The index of coincidence of a column set does not care which alphabet
        # labelled the letters, so ordinary period detection applies unchanged.
        scored = []
        for period in range(2, min(self.max_period, max(2, len(stream) // self.min_letters_per_column)) + 1):
            slices = [stream[i::period] for i in range(period)]
            ic = sum(index_of_coincidence(s) for s in slices if len(s) > 1) / period
            scored.append((ic, period))
        scored.sort(key=lambda t: (-t[0], t[1]))
        return [period for _, period in scored[:6]]

    def crack(self, ciphertext: str, ctx: CrackContext) -> Iterator[Candidate]:
        stream = self.prepare(ciphertext)
        if len(stream) < self.info.min_length:
            return
        hint = ctx.hints.get("key")
        if hint:
            alphabet, keystream = self._params(hint)
            yield ctx.candidate(
                self.name,
                self._transform(stream, alphabet, keystream, -1),
                {"key": self.key_word(alphabet, keystream), "alphabet": alphabet},
                steps=ctx.steps,
                columns=len(keystream),
                method="hint",
            )
            return

        hinted_alphabet = ctx.hints.get("alphabet")
        alphabets = (
            [(str(hinted_alphabet), alphabet_for(str(hinted_alphabet)))]
            if hinted_alphabet
            else list(CANDIDATE_ALPHABETS)
        )
        results: list[Candidate] = []
        for name, alphabet in alphabets:
            if ctx.expired():
                break
            for period in self._periods(stream, ctx):
                if ctx.expired():
                    break
                columns = self._columns(stream, alphabet, period)
                if min((len(c) for c in columns), default=0) < 2:
                    continue
                shifts = [self._solve_column(column, alphabet, ctx) for column in columns]
                plain = self._transform(stream, alphabet, shifts, -1)
                results.append(
                    ctx.candidate(
                        self.name,
                        plain,
                        {"key": self.key_word(alphabet, shifts), "alphabet": alphabet},
                        steps=ctx.steps,
                        columns=period,
                        period=period,
                        alphabet_name=name,
                        method=f"IC period {period}, chi-squared per column over the {name} alphabet",
                    )
                )
        results.sort(key=Candidate.sort_key)
        yield from results[: self.top_candidates]

    def likelihood(self, text: str, ctx: CrackContext) -> float:
        stream = self.prepare(text)
        if len(stream) < self.info.min_length:
            return 0.0
        # Same fingerprint as any periodic cipher: flat whole-text IC that
        # sharpens when the text is sliced by the right period.  The keyed
        # alphabet is invisible to both statistics, which is the point.
        whole = index_of_coincidence(stream)
        if whole > 0.058:
            return 0.0
        best = 0.0
        for period in range(2, min(self.max_period, max(2, len(stream) // 12)) + 1):
            slices = [stream[i::period] for i in range(period)]
            ic = sum(index_of_coincidence(s) for s in slices if len(s) > 1) / period
            best = max(best, ic)
        return round(max(0.0, min(1.0, (best - 0.045) / 0.020)) * 0.8, 4)


class SumClock(_KeyedPeriodic):
    """Several short wheels added together over a keyed alphabet.

    ``K[t] = (q_a[t mod a] + q_b[t mod b] + ...) mod 26``

    The Paradigm Kryptos CTF is built on these: PK3 is a two-wheel sum of
    periods 10 and 8, PK4 a dual clock of 5 and 9, and PK8 a four-wheel sum of
    4, 5, 6 and 7.  They are not just long Vigenères.  Four wheels of 4, 5, 6
    and 7 produce a key of period lcm = 420, so on a 153-letter message no two
    positions share a key symbol and column-wise chi-squared has *nothing* to
    work with -- the classical attack does not merely struggle, it does not
    apply.

    What makes them breakable is that the key is 420 long but only ``4+5+6+7 =
    22`` letters *deep*, and one letter per wheel is gauge (adding one to every
    entry of ``q_4`` and subtracting one from every entry of ``q_5`` leaves the
    sum unchanged), so the true dimension is 19.  Nineteen unknowns against 153
    letters of English is a comfortable margin -- English carries roughly 3.2
    bits of redundancy per letter, so about 28 letters would do -- and the
    difficulty is entirely in the search landscape, not in the evidence.

    So the attack is joint coordinate ascent: hold every wheel but one fixed,
    try all 26 values for one position of it, keep the best by quadgram
    fitness, and sweep until nothing improves.  One sweep is ``26 * sum(periods)``
    decryptions; restarts come from random wheels.
    """

    info = CipherInfo(
        name="sum_clock",
        title="Sum-clock (additive wheels)",
        family=Family.POLYALPHABETIC,
        key_type="wheel periods + wheels",
        keyspace=None,
        deterministic=False,
        min_length=60,
        cost=EXPENSIVE,
        aliases=("multi_clock", "clock", "sumclock", "quagmire_sum"),
        description="Two or more short wheels summed mod 26 over a keyed alphabet. Solved by joint coordinate ascent over the wheels, not by columns.",
        example_key={"periods": [10, 8], "alphabet": "kryptos"},
    )

    #: Wheel-set shapes tried when the key does not name them.  Small periods
    #: and two or three wheels cover every published puzzle of this kind.
    max_single_period = 12
    #: Sweeps without improvement before a restart is abandoned.
    patience = 2

    # -- key handling ------------------------------------------------------- #
    def _params(self, key: Any) -> tuple[str, list[int], list[list[int]] | None]:
        alphabet = KRYPTOS_ALPHABET
        periods: list[int] = [10, 8]
        wheels: list[list[int]] | None = None
        if isinstance(key, dict):
            alphabet = alphabet_for(str(key.get("alphabet", "kryptos")))
            if key.get("periods"):
                periods = [int(p) for p in key["periods"]]
            if key.get("wheels"):
                wheels = [[int(v) % 26 for v in wheel] for wheel in key["wheels"]]
                periods = [len(wheel) for wheel in wheels]
            elif key.get("keys"):
                index = self._index(alphabet)
                wheels = [
                    [index[c] for c in letters_only(str(word)).upper() if c in index]
                    for word in key["keys"]
                ]
                periods = [len(wheel) for wheel in wheels]
        elif isinstance(key, (tuple, list)):
            periods = [int(p) for p in key]
        return alphabet, periods, wheels

    @staticmethod
    def keystream(wheels: Sequence[Sequence[int]], length: int) -> list[int]:
        """Expand the wheels into a keystream of ``length`` symbols."""
        out = []
        for t in range(length):
            total = 0
            for wheel in wheels:
                total += wheel[t % len(wheel)]
            out.append(total % 26)
        return out

    # -- transforms --------------------------------------------------------- #
    def _apply(self, stream: str, alphabet: str, wheels: Sequence[Sequence[int]], sign: int) -> str:
        index = self._index(alphabet)
        out = []
        for t, ch in enumerate(stream):
            position = index.get(ch)
            if position is None:
                out.append(ch)
                continue
            total = 0
            for wheel in wheels:
                total += wheel[t % len(wheel)]
            out.append(alphabet[(position + sign * total) % 26])
        return "".join(out)

    def _default_wheels(self, alphabet: str, periods: Sequence[int]) -> list[list[int]]:
        index = self._index(alphabet)
        words = ["PENTIMENTO", "ORDINATE", "KRYPTOS", "PALIMPSEST"]
        wheels = []
        for i, period in enumerate(periods):
            word = words[i % len(words)]
            wheels.append([index[word[j % len(word)]] for j in range(period)])
        return wheels

    def encrypt(self, plaintext: str, key: Any = None) -> str:
        alphabet, periods, wheels = self._params(key or self.info.example_key)
        wheels = wheels or self._default_wheels(alphabet, periods)
        return self._apply(self.prepare(plaintext), alphabet, wheels, +1)

    def decrypt(self, ciphertext: str, key: Any = None) -> str:
        alphabet, periods, wheels = self._params(key or self.info.example_key)
        wheels = wheels or self._default_wheels(alphabet, periods)
        return self._apply(self.prepare(ciphertext), alphabet, wheels, -1)

    # -- cryptanalysis ------------------------------------------------------ #
    def _ascend(
        self,
        stream: str,
        alphabet: str,
        periods: Sequence[int],
        ctx: CrackContext,
        rng: random.Random,
        wheels: list[list[int]] | None = None,
    ) -> tuple[list[list[int]], float]:
        """Coordinate ascent over the wheels; returns ``(wheels, fitness)``.

        Each step is exact: for one wheel position, every one of the 26 values
        is tried against the quadgram model and the best is kept.  The sweep
        repeats until a full pass changes nothing, which is a local optimum of
        a 19-dimensional landscape rather than of a 420-symbol one.
        """
        index = self._index(alphabet)
        positions = [index.get(ch, 0) for ch in stream]
        n = len(positions)
        wheels = wheels or [[rng.randrange(26) for _ in range(p)] for p in periods]

        def plaintext(current: Sequence[Sequence[int]]) -> str:
            out = []
            for t in range(n):
                total = 0
                for wheel in current:
                    total += wheel[t % len(wheel)]
                out.append(alphabet[(positions[t] - total) % 26])
            return "".join(out)

        best_fit = ctx.model.search_fitness(plaintext(wheels))
        stale = 0
        while stale < self.patience and not ctx.expired():
            improved = False
            for w, period in enumerate(periods):
                for slot in range(period):
                    if ctx.expired():
                        return wheels, best_fit
                    original = wheels[w][slot]
                    local_best, local_fit = original, best_fit
                    for value in range(26):
                        if value == original:
                            continue
                        wheels[w][slot] = value
                        fit = ctx.model.search_fitness(plaintext(wheels))
                        if fit > local_fit + 1e-9:
                            local_best, local_fit = value, fit
                    wheels[w][slot] = local_best
                    if local_fit > best_fit + 1e-9:
                        best_fit, improved = local_fit, True
            stale = 0 if improved else stale + 1
        return wheels, best_fit

    #: Enumerating a short wheel exhaustively costs 26**n; three letters is
    #: 17,576 and four is 456,976.  Beyond that the wheels are taken from a
    #: word list, which is not a guess so much as an observation: PK3's wheels
    #: are literally the words ORDINATE and PENTIMENTO, and the puzzle author
    #: said the key "has quite a lot of entropy, but some structure".
    exhaustive_wheel_letters = 3
    word_list_path = "kryptos/words_{n}.txt"

    def _short_wheel_candidates(self, short: int, alphabet: str, ctx: CrackContext):
        """Candidate values for the enumerated wheel, or None if hopeless."""
        from itertools import product
        from pathlib import Path

        limit = self.exhaustive_wheel_letters
        if short <= limit or (short == 4 and ctx.remaining() > 25.0):
            return product(range(26), repeat=short)
        index = self._index(alphabet)
        path = Path(self.word_list_path.format(n=short))
        if not path.exists():
            return None
        out = []
        for line in path.read_text().splitlines():
            word = line.strip().upper()
            if len(word) == short and all(c in index for c in word):
                out.append([index[c] for c in word])
        return out or None

    def solve_two_wheels(
        self,
        ciphertext: str,
        alphabet: str,
        short: int,
        long: int,
        ctx: CrackContext,
        candidates: Sequence[Sequence[int]] | None = None,
        keep: int = 8,
        verify: int = 300,
    ) -> list[tuple[float, list[list[int]], str]]:
        """Break a two-wheel sum-clock completely, without searching wheel two.

        Two observations make this exact rather than heuristic.

        First, fix the short wheel and the residual is a *plain* Vigenere of
        period ``long``, because only one wheel is left::

            C[t] - q_short[t mod short] = P[t] + q_long[t mod long]

        A Vigenere of known period falls to chi-squared one column at a time,
        so the second wheel is *derived* rather than guessed and the key space
        collapses to an enumeration of the short wheel alone.

        Second, that enumeration need not touch the text at all.  Every
        position's key is ``q_short[t mod short] + q_long[t mod long]``, so
        positions sharing both residues share a key: bin the ciphertext into
        ``lcm(short, long)`` cells once, precompute each cell's log-likelihood
        under all 26 shifts, and a candidate short wheel is then scored with
        ``short * long * 26`` table lookups instead of a walk over the whole
        message.  That is the difference between 500 microseconds and 50 per
        candidate, which is what makes 456,976 of them practical.
        """
        from itertools import product

        stream = self.prepare(ciphertext)
        index = self._index(alphabet)
        positions = [index.get(ch, 0) for ch in stream]
        n = len(positions)
        if n < long * 4:
            return []

        reference = ctx.model.monogram_reference()
        import math

        log_expected = [math.log(max(reference[ch], 1e-6)) for ch in alphabet]

        # cell[(i, j)] -> the letters at positions with those two residues.
        cells: dict[tuple[int, int], list[int]] = {}
        for t in range(n):
            cells.setdefault((t % short, t % long), []).append(positions[t])
        # table[(i, j)][v] = log-likelihood of that cell decrypted by shift v.
        table: dict[tuple[int, int], list[float]] = {}
        for key, letters in cells.items():
            row = [0.0] * 26
            for v in range(26):
                row[v] = sum(log_expected[(letter - v) % 26] for letter in letters)
            table[key] = row
        by_column: list[list[tuple[int, list[float]]]] = [[] for _ in range(long)]
        for (i, j), row in table.items():
            by_column[j].append((i, row))

        if candidates is None:
            candidates = product(range(26), repeat=short)

        scored: list[tuple[float, tuple[int, ...], list[int]]] = []
        for checked, wheel_short in enumerate(candidates, start=1):
            if checked % 8192 == 0 and ctx.expired():
                break
            total = 0.0
            wheel_long: list[int] = []
            for j in range(long):
                best_value, best_score = 0, float("-inf")
                entries = by_column[j]
                for v in range(26):
                    score = 0.0
                    for i, row in entries:
                        score += row[(wheel_short[i] + v) % 26]
                    if score > best_score:
                        best_value, best_score = v, score
                wheel_long.append(best_value)
                total += best_score
            scored.append((total, tuple(wheel_short), wheel_long))
            if len(scored) > verify * 4:
                scored.sort(key=lambda row: -row[0])
                del scored[verify:]

        # Monogram likelihood ranks the candidates; quadgrams decide.  The
        # histogram alone cannot pick the key out of a field this large --
        # measured on PK9-shaped instances, wrong keys beat the true one on
        # letter frequencies -- so the top of that ranking is re-scored on
        # n-grams, which can.
        scored.sort(key=lambda row: -row[0])
        results: list[tuple[float, list[list[int]], str]] = []
        for _total, wheel_short, wheel_long in scored[:verify]:
            plain = "".join(
                alphabet[(positions[t] - wheel_short[t % short] - wheel_long[t % long]) % 26]
                for t in range(n)
            )
            results.append((ctx.model.search_fitness(plain), [list(wheel_short), wheel_long], plain))
        results.sort(key=lambda row: -row[0])
        return results[:keep]

    def _anneal(
        self,
        stream: str,
        alphabet: str,
        periods: Sequence[int],
        ctx: CrackContext,
        rng: random.Random,
        wheels: list[list[int]] | None = None,
        sweeps: int = 260,
    ) -> tuple[list[list[int]], float]:
        """Simulated annealing over the wheels, with incremental rescoring.

        Greedy coordinate ascent is not enough here, and the reason is worth
        recording: one coordinate of a period-4 wheel moves a quarter of the
        message at once, so a climb that has three wheels nearly right and the
        fourth wrong sits in a deep local optimum with no uphill step
        available.  Measured on synthetic 153-letter four-wheel instances with
        known answers, greedy ascent plus kicks recovered 0 of 6.

        Annealing accepts worsening moves early and settles late, which is the
        standard remedy.  The other half of the fix is speed: a candidate move
        changes only the positions in one residue class, so the plaintext is
        edited in place and the n-gram score is recomputed rather than the
        whole text re-derived -- which is what buys the iteration count that
        annealing needs.
        """
        index = self._index(alphabet)
        positions = [index.get(ch, 0) for ch in stream]
        n = len(positions)
        wheels = [list(w) for w in (wheels or [[rng.randrange(26) for _ in range(p)] for p in periods])]

        def build() -> list[str]:
            out = []
            for t in range(n):
                total = 0
                for wheel in wheels:
                    total += wheel[t % len(wheel)]
                out.append(alphabet[(positions[t] - total) % 26])
            return out

        letters = build()
        score = ctx.model.search_fitness("".join(letters))
        best_wheels, best_score = [list(w) for w in wheels], score

        # Temperature schedule: start hot enough to cross a bad wheel (a wrong
        # coordinate costs roughly 0.3-0.6 of fitness), cool to near-greedy.
        start_temp, end_temp = 0.60, 0.02
        total_steps = max(1, sweeps * sum(periods))
        step = 0
        while step < total_steps and not ctx.expired():
            temp = start_temp * ((end_temp / start_temp) ** (step / total_steps))
            step += 1
            w = rng.randrange(len(wheels))
            period = len(wheels[w])
            slot = rng.randrange(period)
            delta = rng.randrange(1, 26)
            old = wheels[w][slot]
            wheels[w][slot] = (old + delta) % 26
            touched = range(slot, n, period)
            previous = [letters[t] for t in touched]
            for t in touched:
                letters[t] = alphabet[(positions[t] - sum(wheel[t % len(wheel)] for wheel in wheels)) % 26]
            trial = ctx.model.search_fitness("".join(letters))
            if trial > score or rng.random() < _accept(trial - score, temp):
                score = trial
                if score > best_score:
                    best_wheels, best_score = [list(x) for x in wheels], score
                    if best_score > SOLVED_FITNESS:
                        return best_wheels, best_score
            else:
                wheels[w][slot] = old
                for t, ch in zip(touched, previous):
                    letters[t] = ch
        # Finish with exact coordinate ascent: annealing lands near the answer,
        # and the last few coordinates are cheaper to settle deterministically.
        return self._ascend(stream, alphabet, periods, ctx, rng, wheels=best_wheels)

    # -- structural constraints on the plaintext ----------------------------- #
    @staticmethod
    def annihilator(periods: Sequence[int]) -> dict[int, int]:
        """Taps of a linear operator that kills any sum-clock of these periods.

        A sum of wheels is annihilated by a composition of two difference
        operators: lag ``lcm(all but one)`` cancels every wheel but one, and a
        further lag equal to that wheel's own period cancels the survivor. For
        periods 4, 5, 6, 7 that is lag 60 (= lcm(4,5,6), and 60 mod 7 = 4) then
        lag 7, giving

            L[t] = s[t+67] - s[t+60] - s[t+7] + s[t]  ==  0   (mod 26)

        The consequence is the useful part. Since ``C = P + K`` and ``L(K) = 0``,

            L(P)[t] = L(C)[t]

        is a condition on the *plaintext* computable from the ciphertext alone
        -- no key, no search. It cannot find a plaintext, but it can test one
        at four operations, which is what makes scanning a whole book for a
        suspected passage practical (measured: 3.4 million letters a second).

        The drop wheel is chosen to minimise the span, because the number of
        usable constraints is ``len(text) - span``.
        """
        best: dict[int, int] | None = None
        for drop in periods:
            others = [p for p in periods if p != drop]
            if not others:
                continue
            first = _lcm(others)
            taps = {0: 1}
            for lag in (first, drop):
                combined: dict[int, int] = {}
                for offset, sign in taps.items():
                    combined[offset] = combined.get(offset, 0) - sign
                    combined[offset + lag] = combined.get(offset + lag, 0) + sign
                taps = {k: v for k, v in combined.items() if v}
            if best is None or max(taps) < max(best):
                best = taps
        return best or {0: 1}

    def plaintext_constraints(
        self,
        ciphertext: str,
        periods: Sequence[int],
        alphabet: str | None = None,
    ) -> list[int]:
        """``L(C)`` -- the values any candidate plaintext must reproduce."""
        alphabet = alphabet or KRYPTOS_ALPHABET
        index = self._index(alphabet)
        stream = [index[c] for c in self.prepare(ciphertext) if c in index]
        taps = self.annihilator(periods)
        span = max(taps)
        return [
            sum(sign * stream[t + off] for off, sign in taps.items()) % 26
            for t in range(len(stream) - span)
        ]

    def scan_corpus(
        self,
        ciphertext: str,
        corpus: str,
        periods: Sequence[int],
        alphabet: str | None = None,
        min_hits: int = 12,
    ) -> list[tuple[int, int, str]]:
        """Find windows of ``corpus`` that could be this ciphertext's plaintext.

        Returns ``(position, constraints satisfied, window)``. A window that
        satisfies twelve constraints by chance is a 26**-12 event, so survivors
        are worth looking at; the true window satisfies all of them.

        This is the attack to reach for when the plaintext is suspected to be a
        known passage -- a quotation, a standard form of words, a page of a
        book -- because it tests that suspicion directly instead of guessing
        cribs.
        """
        alphabet = alphabet or KRYPTOS_ALPHABET
        index = self._index(alphabet)
        target = self.plaintext_constraints(ciphertext, periods, alphabet)
        if not target:
            return []
        taps = sorted(self.annihilator(periods).items())
        text = [c for c in corpus.upper() if c in index]
        values = [index[c] for c in text]
        need = len(self.prepare(ciphertext))
        hits: list[tuple[int, int, str]] = []
        for start in range(len(values) - need + 1):
            matched = 0
            for t, want in enumerate(target):
                total = 0
                for off, sign in taps:
                    total += sign * values[start + t + off]
                if total % 26 != want:
                    break
                matched += 1
            if matched >= min_hits:
                hits.append((start, matched, "".join(text[start : start + need])))
        return hits

    def scan_corpus_partial(
        self,
        ciphertext: str,
        corpus: str,
        periods: Sequence[int],
        alphabet: str | None = None,
        report_from: int = 12,
    ) -> list[tuple[int, int, int, str]]:
        """Like :meth:`scan_corpus`, but tolerant of partial or noisy matches.

        The exact scan asks whether a window *is* the whole plaintext, and
        answers no the moment one letter disagrees. That is too brittle for two
        ordinary situations: a message that quotes only part of a passage, and
        a corpus that is an OCR of a printed book and contains a scanning
        error. Either breaks every constraint after the divergence.

        This reports the longest run of *consecutive* satisfied constraints at
        each alignment, which degrades gracefully instead of collapsing.

        The limit is worth stating precisely, because the obvious guess is
        wrong. Each constraint reads four plaintext positions spanning 67
        characters, so a matching stretch of ``L`` letters yields only
        ``L - 67`` satisfiable constraints -- not ``L``. Measured, with the
        answer planted in a corpus:

        ===============  ==================  ==========
        quoted letters   constraints         detected?
        ===============  ==================  ==========
        74                7                  no
        90               23                  yes
        110              43                  yes
        130              63                  yes
        153 (all)        86                  yes
        ===============  ==================  ==========

        So this finds quotations of roughly eighty-five contiguous letters and
        up. A forty-letter quotation is invisible to it, and no amount of
        scanning will change that -- the information is not there.

        Calibration for judging a result: constraints hold at random with
        probability 1/26, so over a few hundred thousand alignments the longest
        run is about four. Runs past twelve are worth reading; runs past twenty
        are effectively proof.

        Returns ``(position, longest run, constraint offset, window)``.
        """
        alphabet = alphabet or KRYPTOS_ALPHABET
        index = self._index(alphabet)
        target = self.plaintext_constraints(ciphertext, periods, alphabet)
        if not target:
            return []
        taps = sorted(self.annihilator(periods).items())
        span = max(off for off, _ in taps)
        text = [c for c in corpus.upper() if c in index]
        values = [index[c] for c in text]
        if len(values) <= span + len(target):
            return []

        # One pass: the annihilator applied at every corpus position.
        applied = []
        for i in range(len(values) - span):
            total = 0
            for off, sign in taps:
                total += sign * values[i + off]
            applied.append(total % 26)

        need = len(self.prepare(ciphertext))
        checks = len(target)
        hits: list[tuple[int, int, int, str]] = []
        for start in range(len(applied) - checks):
            run = longest = best_at = 0
            run_start = 0
            for t in range(checks):
                if applied[start + t] == target[t]:
                    if run == 0:
                        run_start = t
                    run += 1
                    if run > longest:
                        longest, best_at = run, run_start
                else:
                    run = 0
            if longest >= report_from:
                hits.append((start, longest, best_at, "".join(text[start : start + need])))
        hits.sort(key=lambda row: -row[1])
        return hits

    # -- crib algebra -------------------------------------------------------- #
    #
    # Why a crib is worth so much more here than against an ordinary cipher:
    # the keystream is *linear* in the wheels.  For every position the crib
    # covers,
    #
    #     q_a[t mod a] + q_b[t mod b] + ... == C[t] - P[t]   (mod 26)
    #
    # is one linear equation in the sum(periods) unknowns.  Nineteen effective
    # unknowns for the four-wheel case means a nineteen-letter crib can pin the
    # whole key -- no search at all.  That matters because search is close to
    # hopeless on this structure: every position's key is a *sum* of four
    # unknowns, so moving one coordinate gives no partial credit, and measured
    # annealing plateaus at -6.09 against a true-key fitness of -4.25 no matter
    # how long it runs.

    @staticmethod
    def _solve_mod_prime(rows: list[list[int]], rhs: list[int], width: int, prime: int):
        """Gaussian elimination mod a prime; returns ``(particular, nullspace)``.

        ``None`` when the system is inconsistent.
        """
        matrix = [row[:] + [value] for row, value in zip(rows, rhs)]
        pivots: list[int] = []
        row_index = 0
        for column in range(width):
            pivot = None
            for r in range(row_index, len(matrix)):
                if matrix[r][column] % prime:
                    pivot = r
                    break
            if pivot is None:
                continue
            matrix[row_index], matrix[pivot] = matrix[pivot], matrix[row_index]
            inverse = pow(matrix[row_index][column], prime - 2, prime)
            matrix[row_index] = [(v * inverse) % prime for v in matrix[row_index]]
            for r in range(len(matrix)):
                if r != row_index and matrix[r][column] % prime:
                    factor = matrix[r][column]
                    matrix[r] = [
                        (a - factor * b) % prime for a, b in zip(matrix[r], matrix[row_index])
                    ]
            pivots.append(column)
            row_index += 1
            if row_index == len(matrix):
                break
        for r in range(row_index, len(matrix)):
            if all(v % prime == 0 for v in matrix[r][:width]) and matrix[r][width] % prime:
                return None  # 0 == nonzero: this crib cannot sit here
        particular = [0] * width
        for i, column in enumerate(pivots):
            particular[column] = matrix[i][width] % prime
        free = [c for c in range(width) if c not in pivots]
        nullspace = []
        for f in free:
            vector = [0] * width
            vector[f] = 1
            for i, column in enumerate(pivots):
                vector[column] = (-matrix[i][f]) % prime
            nullspace.append(vector)
        return particular, nullspace, free

    def _crib_solutions(
        self,
        stream: str,
        alphabet: str,
        periods: Sequence[int],
        crib: str,
        offset: int,
        limit: int = 4096,
    ) -> Iterator[list[list[int]]]:
        """Every wheel set consistent with ``crib`` sitting at ``offset``.

        Solved modulo 2 and modulo 13 and recombined by the Chinese remainder
        theorem, because Z/26 is not a field and Gaussian elimination needs
        one.  A short crib leaves a nullspace, which is enumerated -- capped,
        because a five-letter crib on four wheels leaves more solutions than
        anyone wants to score.
        """
        index = self._index(alphabet)
        width = sum(periods)
        offsets: list[int] = []
        base = 0
        for period in periods:
            offsets.append(base)
            base += period

        rows: list[list[int]] = []
        rhs: list[int] = []
        # Fix the gauge before solving.  Adding one to every entry of one wheel
        # and subtracting one from another leaves the keystream -- and so the
        # plaintext -- completely unchanged, so a system with k wheels has k-1
        # free dimensions that mean nothing.  Left in, they multiply the
        # solution set by 26^(k-1): 17,576 identical readings for four wheels,
        # which is what made a correct crib look like it had no solution inside
        # any sane enumeration cap.  Pinning the first slot of every wheel but
        # the first removes them, and costs nothing, because every solution has
        # a gauge-equivalent representative of that form.
        for w in range(1, len(periods)):
            row = [0] * width
            row[offsets[w]] = 1
            rows.append(row)
            rhs.append(0)
        for i, letter in enumerate(crib):
            t = offset + i
            if t >= len(stream):
                return
            if letter not in index or stream[t] not in index:
                continue
            row = [0] * width
            for w, period in enumerate(periods):
                row[offsets[w] + (t % period)] = 1
            rows.append(row)
            rhs.append((index[stream[t]] - index[letter]) % 26)
        if not rows:
            return

        pieces = []
        for prime in (2, 13):
            solved = self._solve_mod_prime(
                [[v % prime for v in row] for row in rows],
                [v % prime for v in rhs],
                width,
                prime,
            )
            if solved is None:
                return
            pieces.append((prime, solved))

        # CRT over the two prime components, enumerating each nullspace.
        from itertools import product

        combos = []
        for prime, (particular, nullspace, _free) in pieces:
            if len(nullspace) > 12:
                return  # far too underdetermined to enumerate honestly
            space = []
            for coefficients in product(range(prime), repeat=len(nullspace)):
                vector = list(particular)
                for c, basis in zip(coefficients, nullspace):
                    if c:
                        vector = [(v + c * b) % prime for v, b in zip(vector, basis)]
                space.append(vector)
                if len(space) > limit:
                    break
            combos.append((prime, space))

        (_p2, space2), (_p13, space13) = combos
        produced = 0
        for v2 in space2:
            for v13 in space13:
                if produced >= limit:
                    return
                produced += 1
                # x == v2 (mod 2), x == v13 (mod 13)  ->  x = 13*v2*13^-1 + 2*v13*2^-1
                solution = [
                    (13 * a + 14 * b) % 26 for a, b in zip(v2, v13)
                ]
                wheels = []
                cursor = 0
                for period in periods:
                    wheels.append(solution[cursor : cursor + period])
                    cursor += period
                yield wheels

    def _crib_subspace(
        self,
        stream: str,
        alphabet: str,
        periods: Sequence[int],
        crib: str,
        offset: int,
    ) -> tuple[list[int], list[list[int]]] | None:
        """``(particular, basis)`` over Z/26 for the wheels a crib allows.

        Where :meth:`_crib_solutions` enumerates the solution set, this returns
        it as an affine subspace so a search can move *inside* it.  That is the
        useful form for a short crib: ten known letters leave far too many
        solutions to list, but they cut the dimension of the problem roughly in
        half, and annealing in nine dimensions is a different proposition from
        annealing in nineteen.
        """
        index = self._index(alphabet)
        width = sum(periods)
        offsets, base = [], 0
        for period in periods:
            offsets.append(base)
            base += period

        rows: list[list[int]] = []
        rhs: list[int] = []
        for w in range(1, len(periods)):
            row = [0] * width
            row[offsets[w]] = 1
            rows.append(row)
            rhs.append(0)
        for i, letter in enumerate(crib):
            t = offset + i
            if t >= len(stream):
                return None
            if letter not in index or stream[t] not in index:
                continue
            row = [0] * width
            for w, period in enumerate(periods):
                row[offsets[w] + (t % period)] = 1
            rows.append(row)
            rhs.append((index[stream[t]] - index[letter]) % 26)

        solutions = {}
        for prime in (2, 13):
            solved = self._solve_mod_prime(
                [[v % prime for v in row] for row in rows],
                [v % prime for v in rhs],
                width,
                prime,
            )
            if solved is None:
                return None
            solutions[prime] = solved
        # Lift both prime components to Z/26 by CRT: 13*x2 + 14*x13.
        particular = [
            (13 * a + 14 * b) % 26
            for a, b in zip(solutions[2][0], solutions[13][0])
        ]
        # Pair the two nullspace bases by free column and CRT them together, so
        # the subspace has one Z/26 generator per free dimension instead of one
        # per prime component.  Keeping them separate works but doubles the
        # search space with generators that only carry a single bit each.
        free2, free13 = solutions[2][2], solutions[13][2]
        by_column_2 = dict(zip(free2, solutions[2][1]))
        by_column_13 = dict(zip(free13, solutions[13][1]))
        basis: list[list[int]] = []
        for column in sorted(set(free2) | set(free13)):
            v2 = by_column_2.get(column, [0] * width)
            v13 = by_column_13.get(column, [0] * width)
            basis.append([(13 * a + 14 * b) % 26 for a, b in zip(v2, v13)])
        return particular, basis

    def crack_with_short_crib(
        self,
        ciphertext: str,
        crib: str,
        ctx: CrackContext,
        periods: Sequence[int],
        alphabet: str | None = None,
        seconds: float = 8.0,
        seed: int = 0,
    ) -> tuple[float, int, list[list[int]], str] | None:
        """Crib algebra for the dimensions it fixes, annealing for the rest.

        A crib long enough to determine the key is a luxury.  A short one still
        pays: it turns the 19-dimensional four-wheel problem into a search over
        the handful of dimensions it leaves free, and annealing that is
        tractable where annealing the whole key is not.
        """
        import math

        stream = self.prepare(ciphertext)
        alphabet = alphabet or KRYPTOS_ALPHABET
        crib = letters_only(crib).upper()
        rng = random.Random(seed or ctx.hints.get("seed", 1))
        deadline = time.time() + seconds
        best: tuple[float, int, list[list[int]], str] | None = None

        for offset in range(0, max(1, len(stream) - len(crib) + 1)):
            if ctx.expired() or time.time() > deadline:
                break
            subspace = self._crib_subspace(stream, alphabet, periods, crib, offset)
            if subspace is None:
                continue
            particular, basis = subspace
            if not basis:
                wheels = self._unflatten(particular, periods)
                plain = self._apply(stream, alphabet, wheels, -1)
                fitness = ctx.model.search_fitness(plain)
                if best is None or fitness > best[0]:
                    best = (fitness, offset, wheels, plain)
                continue

            # Anneal the coefficients of the free directions, not the wheels.
            coefficients = [rng.randrange(26) for _ in basis]

            def materialise(
                values: Sequence[int],
                particular: Sequence[int] = particular,
                basis: Sequence[Sequence[int]] = basis,
            ) -> list[list[int]]:
                flat = list(particular)
                for c, vector in zip(values, basis):
                    if c:
                        flat = [(f + c * v) % 26 for f, v in zip(flat, vector)]
                return self._unflatten(flat, periods)

            current = ctx.model.search_fitness(
                self._apply(stream, alphabet, materialise(coefficients), -1)
            )
            steps = 400 * max(1, len(basis))
            for step in range(steps):
                if ctx.expired() or time.time() > deadline:
                    break
                temp = 0.5 * ((0.02 / 0.5) ** (step / steps))
                i = rng.randrange(len(coefficients))
                previous = coefficients[i]
                # Move set addressing both halves of Z/26 = Z/2 x Z/13
                # separately: each generator carries one bit and one mod-13
                # digit, and a purely random redraw changes both at once,
                # which is too coarse to settle either.
                move = rng.random()
                if move < 0.45:
                    coefficients[i] = rng.randrange(26)
                elif move < 0.70:
                    coefficients[i] = (previous + 13) % 26          # flip the bit
                elif move < 0.90:
                    coefficients[i] = (previous + 2 * rng.randrange(1, 13)) % 26
                else:
                    coefficients[i] = (previous + rng.choice((1, -1))) % 26
                wheels = materialise(coefficients)
                plain = self._apply(stream, alphabet, wheels, -1)
                fitness = ctx.model.search_fitness(plain)
                if fitness > current or rng.random() < math.exp(
                    max(-60.0, (fitness - current) / max(temp, 1e-6))
                ):
                    current = fitness
                    if best is None or fitness > best[0]:
                        best = (fitness, offset, wheels, plain)
                        if fitness > SOLVED_FITNESS:
                            return best
                else:
                    coefficients[i] = previous
        return best

    @staticmethod
    def _unflatten(flat: Sequence[int], periods: Sequence[int]) -> list[list[int]]:
        wheels, cursor = [], 0
        for period in periods:
            wheels.append(list(flat[cursor : cursor + period]))
            cursor += period
        return wheels

    def crack_with_crib(
        self,
        ciphertext: str,
        crib: str,
        ctx: CrackContext,
        periods: Sequence[int] | None = None,
        alphabet: str | None = None,
        offsets: Sequence[int] | None = None,
    ) -> list[tuple[float, int, list[list[int]], str]]:
        """Try a crib at every offset and return the readings, best first.

        Each ``(fitness, offset, wheels, plaintext)`` is a *complete* solution:
        the crib fixes the wheels by algebra and the rest of the message is
        then decrypted with them, so a wrong crib placement shows up
        immediately as an unreadable tail rather than as a plausible fragment.
        """
        stream = self.prepare(ciphertext)
        alphabet = alphabet or KRYPTOS_ALPHABET
        periods = list(periods or [4, 5, 6, 7])
        crib = letters_only(crib).upper()
        out: list[tuple[float, int, list[list[int]], str]] = []
        seen: set[str] = set()
        # Offset 0 first: a crib is usually the opening phrase, and finding it
        # there ends the scan before the other 130 placements are tried.
        span = (
            list(offsets)
            if offsets is not None
            else [0] + list(range(1, max(1, len(stream) - len(crib) + 1)))
        )
        for offset in span:
            if ctx.expired():
                break
            for wheels in self._crib_solutions(stream, alphabet, periods, crib, offset):
                plain = self._apply(stream, alphabet, wheels, -1)
                if plain in seen:
                    continue
                seen.add(plain)
                fitness = ctx.model.search_fitness(plain)
                out.append((fitness, offset, wheels, plain))
                if fitness > SOLVED_FITNESS:
                    # The crib fixed the key and the whole message reads as
                    # English: nothing later can beat that, and a wrong
                    # placement never produces it.
                    out.sort(key=lambda row: -row[0])
                    return out[:50]
        out.sort(key=lambda row: -row[0])
        return out[:50]

    def _wheel_sets(self, ctx: CrackContext, length: int) -> list[list[int]]:
        """Plausible wheel shapes, cheapest first.

        Only coprime-ish small sets are worth trying: two wheels sharing a
        factor waste dimensions (periods 4 and 8 together are no more general
        than a single period-8 wheel), and the published puzzles all use small
        pairwise-coprime periods or a run of consecutive ones.
        """
        hint = ctx.hints.get("periods") or ctx.hints.get("clocks")
        if hint:
            return [[int(p) for p in hint]]
        # First ask the ciphertext what the *combined* period is.  Two wheels
        # of 8 and 10 make a key of period 40, and on a long enough message
        # slicing by 40 sharpens the index of coincidence just as it would for
        # a 40-letter Vigenere key -- so the lcm is detectable even though no
        # single wheel is.  Factoring that lcm back into wheel pairs turns a
        # forty-shape sweep into a three-shape one.  (When the lcm exceeds the
        # message, as it does for four wheels on 153 letters, nothing is
        # detectable and the full list is swept instead.)
        detected: list[list[int]] = []
        ceiling = min(60, max(2, length // 7))
        scored: list[tuple[float, int]] = []
        for period in range(4, ceiling + 1):
            slices = [stream[i::period] for i in range(period)] if (stream := ctx.hints.get("_stream", "")) else []
            if not slices:
                break
            ic = sum(index_of_coincidence(s) for s in slices if len(s) > 1) / period
            scored.append((ic, period))
        scored.sort(key=lambda t: -t[0])
        for _ic, combined in scored[:3]:
            for a, b in combinations(range(3, self.max_single_period + 1), 2):
                if b % a == 0:
                    continue
                if a * b // _gcd(a, b) == combined:
                    detected.append([a, b])

        sets: list[list[int]] = list(detected)
        for a, b in combinations(range(3, self.max_single_period + 1), 2):
            # Only *divisibility* is degenerate: wheels of 4 and 8 sum to
            # something a single period-8 wheel already covers.  Sharing a
            # mere factor is not -- PK3 is periods 10 and 8, gcd 2, lcm 40,
            # and rejecting it for being non-coprime was simply wrong.
            if b % a == 0:
                continue
            if [a, b] not in sets:
                sets.append([a, b])
        # Three- and four-wheel runs: the shapes the Kryptos CTF actually uses.
        for run in ([4, 5, 6, 7], [7, 8, 9], [5, 6, 7], [3, 4, 5], [4, 5, 7], [5, 7, 9]):
            sets.append(list(run))
        # Detected shapes keep their place at the front; the rest are ordered
        # cheapest first.
        rest = sorted((s for s in sets if s not in detected), key=lambda s: (sum(s), len(s)))
        return detected + rest

    def _search(
        self,
        stream: str,
        alphabet: str,
        periods: Sequence[int],
        ctx: CrackContext,
        rng: random.Random,
        restarts: int,
        seconds: float | None = None,
        kicks: int | None = None,
    ) -> tuple[list[list[int]], float] | None:
        """Best wheels for one shape: restarts plus iterated local search.

        Plain restarts are weak here.  One coordinate of one wheel touches
        every position in its residue class -- a quarter of the message for a
        period-4 wheel -- so a single step is a large jump and the landscape is
        correspondingly rugged: a climb that gets three wheels nearly right and
        the fourth wrong has no downhill-free path to the answer.  Iterated
        local search fixes what restarting cannot: keep the incumbent, kick a
        few coordinates at random, re-climb, and accept only improvements.
        """
        deadline = None if seconds is None else time.time() + seconds
        best: tuple[list[list[int]], float] | None = None
        attempts = 0
        while not ctx.expired():
            if deadline is not None and time.time() > deadline:
                break
            if deadline is None and attempts >= restarts:
                break
            attempts += 1
            wheels, fit = self._anneal(stream, alphabet, periods, ctx, rng)
            if best is None or fit > best[1]:
                best = ([list(w) for w in wheels], fit)
            if best[1] > SOLVED_FITNESS:
                return best
            # Kick and re-climb from the incumbent a few times before the next
            # cold start: most of the value is within a few coordinates of a
            # good local optimum, not in another random point.  Scouting passes
            # skip this -- ranking fifty shapes only needs each one's rough
            # ceiling, and paying seven climbs per shape to get it is what
            # spends the budget before the right shape is ever identified.
            for _ in range(self.kicks if kicks is None else kicks):
                if ctx.expired() or (deadline is not None and time.time() > deadline):
                    break
                trial = [list(w) for w in best[0]]
                for _ in range(self.kick_size):
                    w = rng.randrange(len(trial))
                    trial[w][rng.randrange(len(trial[w]))] = rng.randrange(26)
                kicked, kicked_fit = self._anneal(
                    stream, alphabet, periods, ctx, rng, wheels=trial, sweeps=90
                )
                if kicked_fit > best[1]:
                    best = ([list(w) for w in kicked], kicked_fit)
                    if best[1] > SOLVED_FITNESS:
                        return best
        return best

    #: Restarts spent on a wheel shape before it is judged, and again on the
    #: shapes that judged well.  Scouting every shape properly is what runs out
    #: of budget: there are ~50 of them and only one is right, so they are
    #: sampled first and the leaders are then searched hard.
    scout_restarts = 3
    invest_restarts = 30
    #: Perturbation restarts per cold start, and how many wheel positions each
    #: kick randomises.
    kicks = 6
    kick_size = 3
    #: Shapes promoted from scouting to the full search.
    finalists = 4

    def crack(self, ciphertext: str, ctx: CrackContext) -> Iterator[Candidate]:
        stream = self.prepare(ciphertext)
        if len(stream) < self.info.min_length:
            return
        alphabets = (
            [(str(ctx.hints["alphabet"]), alphabet_for(str(ctx.hints["alphabet"])))]
            if ctx.hints.get("alphabet")
            else list(CANDIDATE_ALPHABETS[:2])
        )
        rng = random.Random(ctx.hints.get("seed", 20260929))
        results: list[Candidate] = []

        # A crib changes the problem completely: the keystream is linear in the
        # wheels, so known plaintext turns cryptanalysis into linear algebra
        # and the search is skipped entirely.  Nineteen letters pin a
        # four-wheel key exactly (measured: 5 of 5 synthetic recoveries in
        # 0.1s, against 0 of 6 for annealing given a minute each).
        crib = ctx.hints.get("crib") or ctx.hints.get("known")
        if crib:
            # Shape order matters here, and it is the opposite of the search
            # path's.  Crib algebra is at its most valuable exactly where
            # search fails -- the many-wheel keys whose period exceeds the
            # message -- and those shapes are the *last* thing a sum-ordered
            # sweep reaches.  A pair of wheels, by contrast, the search solves
            # on its own.
            solved = False
            ctx.hints["_stream"] = stream
            shapes = self._wheel_sets(ctx, len(stream))
            # Determined shapes first.  A shape is *solved outright* by the
            # crib when the known letters outnumber its effective unknowns
            # (sum of the periods, less one per wheel for gauge freedom, plus
            # one): that is linear algebra and costs milliseconds.  Everything
            # else falls back to annealing inside a deadline, so putting a
            # single under-determined shape ahead of a determined one spends
            # the whole budget before reaching the answer.  Within each group
            # the many-wheel shapes come first, because that is where search
            # alone fails and the crib is worth most.
            known = len(letters_only(str(crib)))

            def _unknowns(shape: Sequence[int]) -> int:
                return sum(shape) - len(shape) + 1

            if len(shapes) > 1:
                shapes.sort(
                    key=lambda shape: (_unknowns(shape) > known, -len(shape), -sum(shape))
                )
            for _name, alphabet in alphabets:
                for periods in shapes:
                    if ctx.expired():
                        break
                    found = self.crack_with_crib(
                        stream, str(crib), ctx, periods=periods, alphabet=alphabet
                    )
                    for fitness, offset, wheels, plain in found[:3]:
                        results.append(
                            ctx.candidate(
                                self.name,
                                plain,
                                {
                                    "keys": ["".join(alphabet[v] for v in w) for w in wheels],
                                    "periods": list(periods),
                                    "wheels": wheels,
                                    "alphabet": alphabet,
                                },
                                steps=ctx.steps,
                                columns=max(1, sum(periods) - len(periods) + 1),
                                crib=str(crib),
                                crib_offset=offset,
                                fitness_hint=round(fitness, 4),
                                method=f"crib algebra: {len(letters_only(str(crib)))} known letters solved for the wheels",
                            )
                        )
                    if found and found[0][0] > SOLVED_FITNESS:
                        solved = True
                        break
                if solved:
                    break
            if results:
                results.sort(key=Candidate.sort_key)
                yield from results[: self.top_candidates]
                return

        def record(alphabet_name: str, alphabet: str, periods: Sequence[int], wheels: list[list[int]]) -> None:
            results.append(
                ctx.candidate(
                    self.name,
                    self._apply(stream, alphabet, wheels, -1),
                    {
                        "keys": ["".join(alphabet[v] for v in wheel) for wheel in wheels],
                        "periods": list(periods),
                        "wheels": wheels,
                        "alphabet": alphabet,
                    },
                    steps=ctx.steps,
                    columns=max(1, sum(periods) - len(periods) + 1),
                    alphabet_name=alphabet_name,
                    method=(
                        f"joint coordinate ascent over {sum(periods)} wheel positions "
                        f"(periods {list(periods)}, lcm {_lcm(periods)})"
                    ),
                )
            )

        for name, alphabet in alphabets:
            if ctx.expired():
                break
            solved = False
            ctx.hints["_stream"] = stream
            shapes = self._wheel_sets(ctx, len(stream))
            if len(shapes) == 1:
                # The shape was given; spend the whole budget on it.
                found = self._search(
                    stream, alphabet, shapes[0], ctx, rng, self.invest_restarts,
                    seconds=max(1.0, ctx.remaining() * 0.95),
                )
                if found:
                    record(name, alphabet, shapes[0], found[0])
                continue

            # Two-wheel shapes are solved exactly rather than searched: fix
            # the short wheel, derive the long one by chi-squared, done.  This
            # is both faster and *complete*, so it runs before any annealing.
            for periods in shapes:
                if len(periods) != 2 or ctx.expired() or ctx.remaining() < 1.0:
                    continue
                short, long = min(periods), max(periods)
                candidates = self._short_wheel_candidates(short, alphabet, ctx)
                if candidates is None:
                    continue
                exact = self.solve_two_wheels(
                    stream, alphabet, short, long, ctx, candidates=candidates, keep=2
                )
                for fitness, wheels, plain in exact[:1]:
                    results.append(
                        ctx.candidate(
                            self.name,
                            plain,
                            {
                                "keys": ["".join(alphabet[v] for v in w) for w in wheels],
                                "periods": [short, long],
                                "wheels": wheels,
                                "alphabet": alphabet,
                            },
                            steps=ctx.steps,
                            columns=max(1, short + long - 1),
                            alphabet_name=name,
                            method=(
                                f"exact two-wheel solve: enumerated the {short}-wheel, "
                                f"derived the {long}-wheel by chi-squared"
                            ),
                        )
                    )
                    if fitness > SOLVED_FITNESS:
                        results.sort(key=Candidate.sort_key)
                        yield from results[: self.top_candidates]
                        return

            # Stage 1: a few restarts each, to rank the shapes.
            scouted: list[tuple[float, list[int], list[list[int]]]] = []
            for periods in shapes:
                if ctx.expired() or ctx.remaining() < 1.0:
                    break
                if sum(periods) * self.min_letters_per_column > len(stream) * 2:
                    continue  # more unknowns than the text can pay for
                found = self._search(
                    stream, alphabet, periods, ctx, rng, self.scout_restarts, kicks=0
                )
                if found is None:
                    continue
                scouted.append((found[1], list(periods), found[0]))
                if found[1] > SOLVED_FITNESS:
                    record(name, alphabet, periods, found[0])
                    break
            # Stage 2: invest in the shapes that scouted best.  A partial fit
            # is informative -- a wheel set that shares a factor with the true
            # one already explains part of the keystream -- so the leaders are
            # worth an order of magnitude more restarts than the field.
            scouted.sort(key=lambda t: -t[0])
            # Always report the best shape scouting found, even if the clock
            # ran out before it could be searched properly: a partial reading
            # with its wheel shape named is evidence, and returning nothing at
            # all from a finished attack is not.
            if scouted:
                top_fit, top_periods, top_wheels = max(scouted, key=lambda t: t[0])
                record(name, alphabet, top_periods, top_wheels)

            share = max(1.0, ctx.remaining() / max(1, min(self.finalists, len(scouted))))
            for _fit, periods, _wheels in scouted[: self.finalists]:
                if ctx.expired() or ctx.remaining() < 1.0:
                    break
                found = self._search(
                    stream, alphabet, periods, ctx, rng, self.invest_restarts,
                    seconds=min(share, max(1.0, ctx.remaining() * 0.9)),
                )
                if found:
                    record(name, alphabet, periods, found[0])
        results.sort(key=Candidate.sort_key)
        yield from results[: self.top_candidates]

    def likelihood(self, text: str, ctx: CrackContext) -> float:
        stream = self.prepare(text)
        if len(stream) < self.info.min_length:
            return 0.0
        whole = index_of_coincidence(stream)
        if whole > 0.055:
            return 0.0
        # A sum-clock looks like a polyalphabetic with no findable period: the
        # combined period is usually longer than the message, so slicing by any
        # small period does *not* sharpen the IC.  That absence is the signal.
        best = 0.0
        for period in range(2, min(20, max(2, len(stream) // 12)) + 1):
            slices = [stream[i::period] for i in range(period)]
            ic = sum(index_of_coincidence(s) for s in slices if len(s) > 1) / period
            best = max(best, ic)
        flat_everywhere = max(0.0, min(1.0, (0.055 - best) / 0.012))
        # Worth a real share of the budget: this is the only attack in the
        # collection that can read a keystream whose period exceeds the
        # message, and nothing else will find it if this does not run.
        return round(0.85 * flat_everywhere, 4)


def _accept(delta: float, temperature: float) -> float:
    """Metropolis acceptance probability for a worsening move."""
    if temperature <= 0.0:
        return 0.0
    import math

    return math.exp(max(-60.0, delta / temperature))


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


def _lcm(values: Sequence[int]) -> int:
    out = 1
    for value in values:
        out = out * value // _gcd(out, value)
    return out
