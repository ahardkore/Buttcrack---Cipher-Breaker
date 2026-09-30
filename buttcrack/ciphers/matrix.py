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
from itertools import product
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
