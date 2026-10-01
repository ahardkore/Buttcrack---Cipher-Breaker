"""The Hill cipher: linear algebra over Z/26.

Blocks of ``n`` letters are treated as a vector and multiplied by an ``n x n``
key matrix modulo 26.  It is the first cipher in this collection that is
genuinely *polygraphic in every position* -- a single ciphertext letter depends
on ``n`` plaintext letters -- so frequency analysis of single letters tells you
nothing at all.

**The attack.**  The keyspace looks hopeless: 26**(n*n) matrices, of which the
invertible ones number 157,248 for n=2 and about 1.6e12 for n=3.  But
decryption is *row-separable*, and that collapses the problem::

    p[i] = sum_j D[i][j] * c[j]   (mod 26)

Plaintext letter ``i`` of every block depends on row ``i`` of the decryption
matrix and nothing else.  So each row can be scored on its own against the
English letter distribution -- 676 candidate rows for n=2, 17,576 for n=3 --
and only the best few rows per position are combined into whole matrices and
scored with the quadgram model.  A 3x3 Hill that would take 1.6e12 trial
decryptions falls out of ~53,000 row evaluations plus a few thousand full ones.

This is the standard "ciphertext-only Hill" result, and it is why Hill is a
teaching cipher rather than a serious one: linearity leaks position by position.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import suppress
from functools import reduce
from itertools import product
from math import gcd
from typing import Any

from ..results import Candidate
from ..text import A26, letters_only
from .base import EXPENSIVE, Cipher, CipherInfo, CrackContext, Family

#: The 12 units mod 26 -- odd and not a multiple of 13 -- are the only values
#: with a multiplicative inverse, and therefore the only legal determinants.
UNITS = tuple(a for a in range(1, 26, 2) if a % 13 != 0)
INVERSE = {a: next(b for b in range(26) if a * b % 26 == 1) for a in UNITS}


def is_unit(value: int) -> bool:
    """True when ``value`` has a multiplicative inverse mod 26."""
    return value % 26 in INVERSE


def determinant(matrix: list[list[int]]) -> int:
    """Determinant mod 26 of a 2x2 or 3x3 matrix."""
    n = len(matrix)
    if n == 2:
        (a, b), (c, d) = matrix
        return (a * d - b * c) % 26
    (a, b, c), (d, e, f), (g, h, i) = matrix
    return (a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)) % 26


def invert(matrix: list[list[int]]) -> list[list[int]] | None:
    """Matrix inverse mod 26, or ``None`` when the matrix is singular there.

    A matrix is invertible mod 26 exactly when its determinant is coprime with
    26 -- being non-zero is not enough, which is the mistake that makes half the
    Hill implementations on the internet wrong.
    """
    det = determinant(matrix)
    if not is_unit(det):
        return None
    inv_det = INVERSE[det % 26]
    n = len(matrix)
    if n == 2:
        (a, b), (c, d) = matrix
        adj = [[d, -b], [-c, a]]
    else:
        adj = []
        for i in range(3):
            row = []
            for j in range(3):
                minor = [
                    [matrix[r][c] for c in range(3) if c != i]
                    for r in range(3) if r != j
                ]
                row.append(((-1) ** (i + j)) * determinant(minor))
            adj.append(row)
    return [[(inv_det * value) % 26 for value in row] for row in adj]


class Hill(Cipher):
    """The Hill cipher (Lester Hill, 1929), 2x2 and 3x3 blocks."""

    info = CipherInfo(
        name="hill",
        title="Hill cipher (matrix)",
        family=Family.POLYGRAPHIC,
        key_type="matrix or keyword (n*n letters)",
        keyspace=None,
        deterministic=False,
        min_length=40,
        cost=EXPENSIVE,
        aliases=("hill_cipher", "matrix_cipher", "hill2", "hill3"),
        description="Blocks of n letters multiplied by an n x n matrix mod 26. Broken by scoring each decryption-matrix row separately.",
        example_key="HILL",
    )

    #: Rows kept per position before whole matrices are assembled.  Twelve is
    #: comfortably above the rank the true row takes on a 100-letter text in
    #: testing, and keeps 3x3 at 12**3 = 1,728 full evaluations.
    rows_kept = 12
    #: Block sizes attempted, cheapest first.
    block_sizes = (2, 3)

    # -- key handling ------------------------------------------------------- #
    def normalise_key(self, key: Any) -> list[list[int]]:
        """Accept a keyword, a flat sequence or a nested matrix."""
        if isinstance(key, dict):
            key = key.get("matrix") or key.get("key")
        if isinstance(key, str):
            letters = letters_only(key)
            size = int(round(len(letters) ** 0.5))
            if size * size != len(letters) or size not in self.block_sizes:
                raise ValueError(
                    f"a Hill keyword must have n*n letters (4 or 9), got {len(letters)}"
                )
            values = [A26.index(c) for c in letters]
            return [values[i * size : (i + 1) * size] for i in range(size)]
        rows = list(key)
        if rows and not isinstance(rows[0], (list, tuple)):
            size = int(round(len(rows) ** 0.5))
            if size * size != len(rows):
                raise ValueError("a flat Hill key must have n*n entries")
            rows = [list(rows[i * size : (i + 1) * size]) for i in range(size)]
        return [[int(v) % 26 for v in row] for row in rows]

    @staticmethod
    def key_word(matrix: list[list[int]]) -> str:
        return "".join(A26[v % 26] for row in matrix for v in row)

    # -- transforms --------------------------------------------------------- #
    def _apply(self, stream: str, matrix: list[list[int]]) -> str:
        n = len(matrix)
        values = [A26.index(c) for c in stream]
        # Hill needs whole blocks; X is the traditional pad.
        if len(values) % n:
            values += [A26.index("X")] * (n - len(values) % n)
        out = []
        for start in range(0, len(values), n):
            block = values[start : start + n]
            for row in matrix:
                out.append(A26[sum(r * v for r, v in zip(row, block)) % 26])
        return "".join(out)

    def encrypt(self, plaintext: str, key: Any = "HILL") -> str:
        return self._apply(self.prepare(plaintext), self.normalise_key(key))

    def decrypt(self, ciphertext: str, key: Any = "HILL") -> str:
        matrix = self.normalise_key(key)
        inverse = invert(matrix)
        if inverse is None:
            raise ValueError(
                f"key matrix is not invertible mod 26 (determinant {determinant(matrix)}); "
                "its determinant must be odd and not a multiple of 13"
            )
        return self._apply(self.prepare(ciphertext), inverse)

    # -- cryptanalysis ------------------------------------------------------ #
    def _score_rows(
        self, blocks: list[list[int]], size: int, position: int, ctx: CrackContext
    ) -> list[tuple[float, tuple[int, ...]]]:
        """Rank every candidate decryption-matrix row by letter-frequency fit.

        ``p[position]`` of each block is ``row . block``; a whole row can
        therefore be judged without knowing any other row, which is what makes
        the search affordable.  Chi-squared against English monograms is the
        metric -- it is one histogram per row, no n-grams.
        """
        ref = ctx.model.monogram_reference()
        expected = [ref[A26[i]] * len(blocks) for i in range(26)]
        scored: list[tuple[float, tuple[int, ...]]] = []
        for row in product(range(26), repeat=size):
            if all(v == 0 for v in row):
                continue  # a zero row cannot be part of an invertible matrix
            counts = [0] * 26
            for block in blocks:
                total = 0
                for r, v in zip(row, block):
                    total += r * v
                counts[total % 26] += 1
            chi = 0.0
            for i in range(26):
                exp = expected[i]
                if exp > 0:
                    diff = counts[i] - exp
                    chi += diff * diff / exp
            scored.append((chi, row))
        scored.sort(key=lambda t: t[0])
        return scored[: self.rows_kept]

    def crack(self, ciphertext: str, ctx: CrackContext) -> Iterator[Candidate]:
        stream = self.prepare(ciphertext)
        if len(stream) < self.info.min_length and not ctx.exhaustive:
            return

        hint = ctx.hints.get("key")
        if hint:
            with suppress(ValueError):  # a singular hint matrix is the user's mistake
                yield ctx.candidate(
                    self.name, self.decrypt(stream, hint),
                    {"matrix": self.normalise_key(hint)}, steps=ctx.steps, method="hint",
                )
            return

        results: list[Candidate] = []
        for size in self.block_sizes:
            if ctx.expired():
                break
            usable = len(stream) - len(stream) % size
            if usable < size * 12:
                continue  # too few blocks for the row statistics to separate
            # Row scoring is O(26**size * blocks); cap the sample so 3x3 on a
            # long text stays inside its slice of the budget.
            sample = stream[: min(usable, 1200 - 1200 % size)]
            blocks = [
                [A26.index(c) for c in sample[i : i + size]]
                for i in range(0, len(sample), size)
            ]
            per_position = []
            for position in range(size):
                if ctx.expired():
                    return
                per_position.append(self._score_rows(blocks, size, position, ctx))

            seen: set[tuple] = set()
            for combo in product(*per_position):
                if ctx.expired():
                    break
                decryption = [list(row) for _, row in combo]
                key = tuple(tuple(r) for r in decryption)
                if key in seen:
                    continue
                seen.add(key)
                encryption = invert(decryption)
                if encryption is None:
                    continue  # rows that look good but do not form a key
                plain = self._apply(stream, decryption)
                results.append(
                    ctx.candidate(
                        self.name,
                        plain,
                        {"matrix": encryption, "keyword": self.key_word(encryption)},
                        steps=ctx.steps,
                        block_size=size,
                        decryption_matrix=decryption,
                        method=f"separable row search ({size}x{size}), chi-squared rows then quadgram ranking",
                    )
                )
            results.sort(key=Candidate.sort_key)
            # A solved 2x2 makes the 3x3 sweep pointless, and 3x3 is the
            # expensive half of this attack.
            if results and results[0].confidence >= 0.86:
                break
        results.sort(key=Candidate.sort_key)
        yield from results[: self.top_candidates]

    def likelihood(self, text: str, ctx: CrackContext) -> float:
        stream = self.prepare(text)
        n = len(stream)
        if n < self.info.min_length:
            return 0.0
        from ..text import index_of_coincidence

        ic = index_of_coincidence(stream)
        # Hill flattens single-letter statistics almost to random (each output
        # letter is a sum of n inputs), so a near-random IC on letters-only text
        # is the signal.  Below 0.05 is the interesting band; English is 0.067.
        flat = max(0.0, min(1.0, (0.062 - ic) / 0.020))
        # Length divisible by the block size is weak corroboration: Hill output
        # is always a whole number of blocks.
        divisible = 0.5 + 0.5 * any(n % size == 0 for size in self.block_sizes)
        return round(0.8 * flat * divisible, 4)


class KeyedHill(Cipher):
    """Hill over a *keyed* alphabet, with an optional Quagmire III layer.

    Two small changes to :class:`Hill` put a puzzle out of its reach, and both
    of them are standard in Kryptos-style constructions (the Paradigm Kryptos
    CTF's PK7 is exactly this shape: ``Quagmire III (period 6) then Hill 3x3``,
    both over the sculpture's own alphabet)::

        idx(c_block) = M . (idx(p_block) + k[pos mod P])      idx = index in a
                                                              *keyed* alphabet

    *Keyed indices.*  ``A`` is not 0; in ``KRYPTOSABCDEFGHIJLMNQUVWXZ`` it is 7.
    Relabelling the alphabet is an arbitrary permutation of Z/26, and it does
    not commute with the matrix multiply, so a solver that assumes ``A=0``
    is not solving a harder instance of the same problem -- it is solving a
    different, wrong one.  Every row it scores is a linear functional of the
    wrong symbols, which is why the plain Hill attack returns noise.

    *The additive layer.*  A Quagmire III (a Vigenère in keyed space) in front
    of the matrix adds a position-dependent constant.  It stays linear, so the
    composite is still an affine map per block -- but the constant now depends
    on ``pos mod P``, which smears each row's letter histogram across two or
    more shifted copies of itself and destroys the chi-squared signal the plain
    Hill attack depends on.

    **The attack.**  Both changes are absorbed by keeping the separability that
    breaks Hill in the first place.  Writing ``D = M^-1``, decryption is::

        p[i] = sum_j D[i][j] * c[j]  -  k[block*n + i mod P]

    so plaintext position ``i`` still depends on row ``i`` of ``D`` alone, plus
    one shift per *phase* (``block mod P/n``).  For each candidate row the
    blocks are split by phase, one histogram is built per phase, and each phase
    is allowed its own best shift before the chi-squared is summed.  A row that
    is right scores well in every phase at once; a row that is wrong cannot be
    rescued by any choice of shift.

    Two details make it affordable.  The row histogram does not depend on *which*
    position the row decrypts -- it is the same statistic for all of them -- so
    one ranking of 17,576 rows serves the whole matrix.  And the phase shifts
    recovered from single letters are only a starting point: the assembled
    matrices are re-ranked on quadgrams, and the best few have their Quagmire
    key polished position by position, which fixes the shifts that monogram
    statistics alone leave one or two off.
    """

    info = CipherInfo(
        name="keyed_hill",
        title="Hill over a keyed alphabet (+ Quagmire III)",
        family=Family.POLYGRAPHIC,
        key_type="matrix + keyword + alphabet",
        keyspace=None,
        deterministic=False,
        min_length=72,
        cost=EXPENSIVE,
        aliases=(
            "hill_keyed",
            "quagmire_hill",
            "quagmire3_hill",
            "kryptos_hill",
            "hill_quagmire",
        ),
        description=(
            "Hill blocks over a keyed (KRYPTOS-style) alphabet, optionally behind a "
            "Quagmire III keyword. Broken by phase-split row separation: one chi-squared "
            "histogram per row per phase, then quadgram assembly and key polish."
        ),
        example_key={"matrix": "ALCHEMIST", "key": "ANNEAL", "alphabet": "kryptos"},
    )

    #: Rows kept per position before whole matrices are assembled.
    rows_kept = 10
    #: Block sizes attempted.  3x3 is the interesting one; 2x2 is nearly free.
    block_sizes = (3, 2)
    #: Quagmire periods attempted, in blocks.  ``1`` means a single constant
    #: (plain Hill, or Hill behind a period-n keyword); ``2`` covers the common
    #: "period 6 over 3x3 blocks" construction.
    phase_counts = (1, 2)
    #: Assembled matrices that get the expensive key polish.
    polish_top = 5

    # -- key handling ------------------------------------------------------- #
    def prepare(self, text: str) -> str:
        return letters_only(text).upper()

    def _params(self, key: Any) -> tuple[str, list[list[int]], list[int]]:
        """Return ``(alphabet, matrix, shifts)`` -- all in keyed-index space."""
        from .keyed import KRYPTOS_ALPHABET, alphabet_for

        alphabet = KRYPTOS_ALPHABET
        matrix: Any = None
        word: Any = ""
        shifts: Any = None
        if isinstance(key, dict):
            alphabet = alphabet_for(str(key.get("alphabet", "kryptos")))
            matrix = key.get("matrix") or key.get("hill") or key.get("key")
            word = key.get("keyword") or key.get("quagmire") or ""
            if not isinstance(matrix, (str, list, tuple)):
                matrix = None
            if key.get("matrix") is not None and key.get("key") is not None:
                word = key.get("key")
            shifts = key.get("shifts")
        elif isinstance(key, (tuple, list)) and len(key) >= 2 and isinstance(key[0], str):
            matrix, word = key[0], key[1]
            if len(key) >= 3:
                alphabet = alphabet_for(str(key[2]))
        else:
            matrix = key
        if matrix is None:
            raise ValueError("a keyed Hill key needs a matrix (n*n letters or numbers)")
        index = {ch: i for i, ch in enumerate(alphabet)}
        if isinstance(matrix, str):
            letters = letters_only(matrix).upper()
            size = int(round(len(letters) ** 0.5))
            if size * size != len(letters) or size not in self.block_sizes:
                raise ValueError(
                    f"a Hill keyword must have n*n letters (4 or 9), got {len(letters)}"
                )
            values = [index[c] for c in letters]
            rows = [values[i * size : (i + 1) * size] for i in range(size)]
        else:
            rows = list(matrix)
            if rows and not isinstance(rows[0], (list, tuple)):
                size = int(round(len(rows) ** 0.5))
                if size * size != len(rows):
                    raise ValueError("a flat Hill key must have n*n entries")
                rows = [list(rows[i * size : (i + 1) * size]) for i in range(size)]
            rows = [[int(v) % 26 for v in row] for row in rows]
        if shifts is None:
            text = letters_only(str(word or "")).upper()
            shifts = [index[c] for c in text if c in index] or [0]
        else:
            shifts = [int(v) % 26 for v in shifts] or [0]
        return alphabet, rows, list(shifts)

    @staticmethod
    def key_word(alphabet: str, values) -> str:
        """Render matrix rows or a shift list back as letters of the alphabet."""
        flat = []
        for item in values:
            flat.extend(item if isinstance(item, (list, tuple)) else [item])
        return "".join(alphabet[int(v) % 26] for v in flat)

    # -- transforms --------------------------------------------------------- #
    def _apply(
        self,
        stream: str,
        alphabet: str,
        matrix: list[list[int]],
        shifts: list[int],
        sign: int,
    ) -> str:
        """Add the keystream then multiply (``sign=+1``), or the inverse order."""
        index = {ch: i for i, ch in enumerate(alphabet)}
        n = len(matrix)
        values = [index[c] for c in stream if c in index]
        if len(values) % n:
            values += [index["X"]] * (n - len(values) % n)
        period = len(shifts)
        out: list[str] = []
        for start in range(0, len(values), n):
            block = values[start : start + n]
            if sign > 0:  # encrypt: Quagmire first, then the matrix
                block = [(v + shifts[(start + i) % period]) % 26 for i, v in enumerate(block)]
                for row in matrix:
                    out.append(alphabet[sum(r * v for r, v in zip(row, block)) % 26])
            else:  # decrypt: the inverse matrix, then subtract the keystream
                for i, row in enumerate(matrix):
                    value = sum(r * v for r, v in zip(row, block)) % 26
                    out.append(alphabet[(value - shifts[(start + i) % period]) % 26])
        return "".join(out)

    def encrypt(self, plaintext: str, key: Any = None) -> str:
        alphabet, matrix, shifts = self._params(key or self.info.example_key)
        return self._apply(self.prepare(plaintext), alphabet, matrix, shifts, +1)

    def decrypt(self, ciphertext: str, key: Any = None) -> str:
        alphabet, matrix, shifts = self._params(key or self.info.example_key)
        inverse = invert(matrix)
        if inverse is None:
            raise ValueError(
                f"key matrix is not invertible mod 26 (determinant {determinant(matrix)}); "
                "its determinant must be odd and not a multiple of 13"
            )
        return self._apply(self.prepare(ciphertext), alphabet, inverse, shifts, -1)

    # -- cryptanalysis ------------------------------------------------------ #
    @staticmethod
    def _blocks(stream: str, alphabet: str, size: int) -> list[list[int]]:
        index = {ch: i for i, ch in enumerate(alphabet)}
        values = [index[c] for c in stream if c in index]
        usable = len(values) - len(values) % size
        return [values[i : i + size] for i in range(0, usable, size)]

    #: Rows that survive the shift-invariant filter and get the full
    #: chi-squared-over-shifts treatment.  The filter is exact about what it
    #: discards: a row whose histogram is flat cannot be made English by any
    #: choice of shift, because a shift permutes the histogram and leaves its
    #: index of coincidence alone.
    rows_probed = 500

    def _row_tables(
        self,
        blocks: list[list[int]],
        size: int,
        alphabet: str,
        ctx: CrackContext,
    ) -> dict[int, list[tuple[float, tuple[int, ...], tuple[int, ...]]]]:
        """Rank decryption rows for every phase count, in one sweep.

        The histogram of ``row . block`` is the same statistic whichever
        plaintext position the row decrypts, so one ranking serves all ``size``
        positions of the matrix.  Splitting the blocks by phase costs nothing
        extra -- the per-phase histograms are built in the same pass and simply
        added back together for the no-Quagmire case.

        Two stages, because the shift search is the expensive half:

        1. *Shift-invariant filter.*  The index of coincidence of a histogram
           does not change when the histogram is rotated, so it judges a row
           without trying 26 shifts.  English sits near 0.066 and a wrong row
           near 0.038, and only the top few hundred rows go further.
        2. *Chi-squared per phase.*  Each phase picks its own best shift, and
           the row's score is the sum -- a right row fits every phase at once.
        """
        reference = ctx.model.monogram_reference()
        # Expected proportions re-indexed into the keyed alphabet: English says
        # E is common, and E is index 9 of the Kryptos alphabet, not 4.
        expected = [reference[ch] for ch in alphabet]
        phase_counts = [p for p in self.phase_counts if len(blocks) // p >= 12]
        if not phase_counts:
            return {}
        widest = max(phase_counts)
        grouped = [[b for i, b in enumerate(blocks) if i % widest == phase] for phase in range(widest)]
        columns = [[[b[j] for b in group] for j in range(size)] for group in grouped]
        sizes = [len(group) for group in grouped]

        # -- stage 1: one pass over every row, pruned by histogram IC -------- #
        probed: list[tuple[float, tuple[int, ...], list[list[int]]]] = []
        worst = -1.0
        checked = 0
        for row in product(range(26), repeat=size):
            # A row whose entries share a factor with 26 cannot belong to an
            # invertible matrix, and its output lands on a coset -- every
            # second residue, or only 0 and 13 -- which makes it *look* like
            # the least flat histogram in the sweep.  Dropping these rows both
            # removes the decoys and cuts the sweep by a tenth.
            if gcd(reduce(gcd, row), 26) != 1:
                continue
            checked += 1
            if checked % 2048 == 0 and ctx.expired():
                break
            histograms = []
            flatness = 0.0
            for phase in range(widest):
                counts = [0] * 26
                cols = columns[phase]
                total = sizes[phase]
                acc = [0] * total
                for j, coefficient in enumerate(row):
                    if not coefficient:
                        continue
                    column = cols[j]
                    for i in range(total):
                        acc[i] += coefficient * column[i]
                for value in acc:
                    counts[value % 26] += 1
                histograms.append(counts)
                squares = sum(v * v for v in counts)
                flatness += (squares - total) / (total * (total - 1)) if total > 1 else 0.0
            if len(probed) < self.rows_probed or flatness > worst:
                probed.append((flatness, row, histograms))
                if len(probed) > self.rows_probed * 2:
                    probed.sort(key=lambda t: -t[0])
                    del probed[self.rows_probed :]
                    worst = probed[-1][0]
        probed.sort(key=lambda t: -t[0])
        del probed[self.rows_probed :]

        # -- stage 2: chi-squared, one shift per phase ----------------------- #
        def best_shift(counts: list[int], total: int) -> tuple[float, int]:
            exp = [p * total for p in expected]
            best_chi, best = float("inf"), 0
            for shift in range(26):
                chi = 0.0
                for i in range(26):
                    e = exp[i]
                    if e > 0:
                        diff = counts[(i + shift) % 26] - e
                        chi += diff * diff / e
                if chi < best_chi:
                    best_chi, best = chi, shift
            return best_chi, best

        tables: dict[int, list[tuple[float, tuple[int, ...], tuple[int, ...]]]] = {}
        for phases in phase_counts:
            scored: list[tuple[float, tuple[int, ...], tuple[int, ...]]] = []
            for _, row, histograms in probed:
                chi_total, shifts = 0.0, []
                for phase in range(phases):
                    # Phases of a coarser split are sums of the finest ones.
                    counts = [0] * 26
                    total = 0
                    for source in range(phase, widest, phases):
                        total += sizes[source]
                        for i, v in enumerate(histograms[source]):
                            counts[i] += v
                    chi, shift = best_shift(counts, total)
                    chi_total += chi
                    shifts.append(shift)
                scored.append((chi_total, row, tuple(shifts)))
            scored.sort(key=lambda t: t[0])
            tables[phases] = scored[: self.rows_kept]
        return tables

    def _polish(
        self,
        blocks: list[list[int]],
        alphabet: str,
        decryption: list[list[int]],
        shifts: list[int],
        ctx: CrackContext,
    ) -> list[int]:
        """Coordinate ascent on the Quagmire key, one position at a time.

        Monogram statistics place each shift to within a letter or two on a
        short text; quadgrams settle it.  One sweep is ``26 * len(shifts)``
        decryptions, which is nothing next to the row sweep.
        """
        shifts = list(shifts)
        best = ctx.model.search_fitness(self._decode(blocks, alphabet, decryption, shifts))
        for _ in range(2):
            improved = False
            for position in range(len(shifts)):
                if ctx.expired():
                    return shifts
                original = shifts[position]
                for value in range(26):
                    if value == original:
                        continue
                    shifts[position] = value
                    fitness = ctx.model.search_fitness(
                        self._decode(blocks, alphabet, decryption, shifts)
                    )
                    if fitness > best:
                        best, original, improved = fitness, value, True
                shifts[position] = original
            if not improved:
                break
        return shifts

    @staticmethod
    def _decode(
        blocks: list[list[int]],
        alphabet: str,
        decryption: list[list[int]],
        shifts: list[int],
    ) -> str:
        size = len(decryption)
        period = len(shifts)
        out: list[str] = []
        for b, block in enumerate(blocks):
            base = b * size
            for i, row in enumerate(decryption):
                value = sum(r * v for r, v in zip(row, block)) % 26
                out.append(alphabet[(value - shifts[(base + i) % period]) % 26])
        return "".join(out)

    def crack(self, ciphertext: str, ctx: CrackContext) -> Iterator[Candidate]:
        from .keyed import CANDIDATE_ALPHABETS, alphabet_for

        stream = self.prepare(ciphertext)
        if len(stream) < self.info.min_length and not ctx.exhaustive:
            return

        hint = ctx.hints.get("key")
        if hint:
            with suppress(ValueError):
                alphabet, matrix, shifts = self._params(hint)
                yield ctx.candidate(
                    self.name,
                    self.decrypt(stream, hint),
                    {
                        "matrix": self.key_word(alphabet, matrix),
                        "key": self.key_word(alphabet, shifts),
                        "alphabet": alphabet,
                    },
                    steps=ctx.steps,
                    method="hint",
                )
            return

        hinted = ctx.hints.get("alphabet")
        alphabets = (
            [(str(hinted), alphabet_for(str(hinted)))]
            if hinted
            else list(CANDIDATE_ALPHABETS[:2] if not ctx.exhaustive else CANDIDATE_ALPHABETS)
        )
        hinted_period = ctx.hints.get("key_length") or ctx.hints.get("period")

        results: list[Candidate] = []
        for name, alphabet in alphabets:
            if ctx.expired():
                break
            for size in self.block_sizes:
                blocks = self._blocks(stream, alphabet, size)
                if len(blocks) < 24:
                    continue
                # One sweep over the 26**size candidate rows serves every
                # position of the matrix and every phase count.
                tables = self._row_tables(blocks, size, alphabet, ctx)
                for phases, rows in sorted(tables.items()):
                    if ctx.expired():
                        break
                    period = size * phases
                    if hinted_period and int(hinted_period) not in (period, phases):
                        continue
                    if not rows:
                        continue
                    assembled: list[tuple[float, list[list[int]], list[int]]] = []
                    seen: set[tuple] = set()
                    for combo in product(rows, repeat=size):
                        if ctx.expired():
                            break
                        decryption = [list(row) for _, row, _ in combo]
                        fingerprint = tuple(tuple(r) for r in decryption)
                        if fingerprint in seen:
                            continue
                        seen.add(fingerprint)
                        if invert(decryption) is None:
                            continue  # rows that look good but do not form a key
                        shifts = [0] * period
                        for i, (_, _, phase_shifts) in enumerate(combo):
                            for phase, shift in enumerate(phase_shifts):
                                shifts[phase * size + i] = shift
                        plain = self._decode(blocks, alphabet, decryption, shifts)
                        assembled.append((ctx.model.search_fitness(plain), decryption, shifts))
                    assembled.sort(key=lambda t: -t[0])
                    for _, decryption, shifts in assembled[: self.polish_top]:
                        if ctx.expired():
                            break
                        shifts = self._polish(blocks, alphabet, decryption, shifts, ctx)
                        encryption = invert(decryption)
                        if encryption is None:
                            continue
                        plain = self._decode(blocks, alphabet, decryption, shifts)
                        results.append(
                            ctx.candidate(
                                self.name,
                                plain,
                                {
                                    "matrix": self.key_word(alphabet, encryption),
                                    "key": self.key_word(alphabet, shifts),
                                    "alphabet": alphabet,
                                },
                                steps=ctx.steps,
                                block_size=size,
                                period=period,
                                alphabet_name=name,
                                decryption_matrix=decryption,
                                method=(
                                    f"phase-split row search ({size}x{size}, period {period}) "
                                    f"over the {name} alphabet, then quadgram key polish"
                                ),
                            )
                        )
                    results.sort(key=Candidate.sort_key)
                    if results and results[0].confidence >= 0.86:
                        yield from results[: self.top_candidates]
                        return
        results.sort(key=Candidate.sort_key)
        yield from results[: self.top_candidates]

    def likelihood(self, text: str, ctx: CrackContext) -> float:
        """Flat letter statistics *plus* repeats that line up on a block grid.

        A polygraphic block cipher leaks one thing even when the letters look
        random: a repeated plaintext block comes out as a repeated ciphertext
        block, and those repeats land on multiples of the block size.  Counting
        aligned repeats against the number expected by chance separates a Hill
        (or a Hill behind a Quagmire) from a stream cipher or a long Vigenère,
        neither of which has a block grid to line up on.
        """
        from ..text import index_of_coincidence

        stream = self.prepare(text)
        n = len(stream)
        if n < self.info.min_length:
            return 0.0
        ic = index_of_coincidence(stream)
        flat = max(0.0, min(1.0, (0.060 - ic) / 0.018))
        if not flat:
            return 0.0
        best_ratio = 0.0
        for size in self.block_sizes:
            count = n // size
            if count < 24:
                continue
            blocks: dict[str, int] = {}
            for i in range(0, count * size, size):
                block = stream[i : i + size]
                blocks[block] = blocks.get(block, 0) + 1
            pairs = sum(v * (v - 1) / 2 for v in blocks.values())
            expected = count * (count - 1) / 2 / (26.0**size)
            if expected > 0:
                best_ratio = max(best_ratio, (pairs - expected) / max(1.0, expected))
        aligned = max(0.0, min(1.0, best_ratio / 4.0))
        return round(0.55 * flat * (0.35 + 0.65 * aligned), 4)
