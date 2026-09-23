"""Polyalphabetic ciphers: Vigenere, Beaufort, Variant, Gronsfeld, Trithemius, Autokey.

The attack is the textbook one, and it works:

1. **Find the period.**  Friedman's index-of-coincidence test scores every
   candidate key length by how English its cosets look (a correct period splits
   the text into monoalphabetic columns with IC ~ 0.066).  Kasiski examination
   -- the gcd of distances between repeated trigrams -- corroborates it and often
   wins on short texts.
2. **Solve each column.**  Every column is a Caesar shift, so chi-squared against
   the English letter distribution picks it directly.
3. **Refine with n-grams.**  Chi-squared is a per-column decision made on a
   fraction of the text and gets individual letters wrong on anything under ~300
   characters.  A coordinate-ascent pass over the key, maximising whole-text
   quadgram fitness, fixes those.  This step is what makes short Vigenere texts
   solvable rather than "nearly solvable".

Autokey is different -- the key is the plaintext itself -- and is solved by
splitting into independent chains and hill climbing the primer.
"""

from __future__ import annotations

from collections import Counter
from math import gcd
from typing import Any, Iterable, Iterator

from ..results import Candidate
from ..text import A26, best_key_length, ic_of_columns, index_of_coincidence, letters_only, map_letters
from .base import CHEAP, MODERATE, Cipher, CipherInfo, CrackContext, Family

ENGLISH_IC = 0.0667
RANDOM_IC = 0.0385


# --------------------------------------------------------------------------- #
# period finding
# --------------------------------------------------------------------------- #
def kasiski(text: str, max_len: int = 24, min_repeat_len: int = 3) -> list[tuple[int, int]]:
    """Kasiski examination: score key lengths by repeated-sequence distances.

    Returns ``[(length, votes)]`` ordered by votes.  A repeated n-gram in the
    ciphertext usually means the same key letters encrypted the same plaintext,
    so the distance between the repeats is a multiple of the key length.
    """
    votes: Counter = Counter()
    seen: dict[str, list[int]] = {}
    n = len(text)
    for size in range(min_repeat_len, min(12, n // 4) + 1):
        for i in range(n - size + 1):
            seen.setdefault(text[i : i + size], []).append(i)
    for positions in seen.values():
        if len(positions) < 2:
            continue
        for a in range(len(positions)):
            for b in range(a + 1, len(positions)):
                d = positions[b] - positions[a]
                for k in range(2, min(max_len, d) + 1):
                    if d % k == 0:
                        votes[k] += 1
    return votes.most_common()


#: Shorter texts get every key length tried rather than the IC ranking's top few.
SWEEP_PERIOD_LETTERS = 400
#: A period whose columns hold fewer letters than this is not worth solving.
MIN_LETTERS_PER_COLUMN = 4


def candidate_key_lengths(
    text: str, max_len: int = 20, min_letters_per_column: int = 8
) -> list[tuple[int, float, str]]:
    """Rank plausible key lengths, fusing the IC test with Kasiski evidence.

    Returns ``[(length, score, evidence)]`` best first.  Divisors of a strong
    period are promoted, because IC also peaks at multiples of the true length.
    """
    stream = letters_only(text)
    n = len(stream)
    if n < 4:
        return []
    max_len = max(2, min(max_len, n // max(min_letters_per_column, 2), 40))
    ic_scores = {k: ic_of_columns(stream, k) for k in range(1, max_len + 1)}
    ic_best = max(ic_scores.values())
    ic_worst = min(ic_scores.values())
    span = (ic_best - ic_worst) or 1.0
    kas_votes = dict(kasiski(stream, max_len))
    kas_max = max(kas_votes.values()) if kas_votes else 1

    ranked: list[tuple[int, float, str]] = []
    for k, ic in ic_scores.items():
        ic_norm = (ic - RANDOM_IC) / (ENGLISH_IC - RANDOM_IC)
        kas_norm = kas_votes.get(k, 0) / kas_max
        # A period is credible if its columns look English; Kasiski adds support.
        score = max(0.0, min(1.0, ic_norm)) * 0.8 + kas_norm * 0.2
        evidence = f"ic={ic:.4f}" + (f" kasiski={kas_votes[k]}" if k in kas_votes else "")
        ranked.append((k, score, evidence))
    ranked.sort(key=lambda t: (-t[1], t[0]))
    # Drop multiples of an equally good shorter period.
    out: list[tuple[int, float, str]] = []
    for k, score, ev in ranked:
        if any(k % j == 0 and s >= score * 0.93 for j, s, _ in out):
            continue
        out.append((k, score, ev))
    return out


# --------------------------------------------------------------------------- #
# periodic ciphers
# --------------------------------------------------------------------------- #
class PeriodicCipher(Cipher):
    """Base class for ciphers whose key repeats with a fixed period."""

    #: how the key letter combines with the plaintext letter
    mode = "vigenere"
    max_key_length = 20
    key_alphabet_size = 26

    def _shift_for(self, plain: int, cipher: int) -> int:
        raise NotImplementedError

    def _decrypt_letter(self, c: int, k: int) -> int:
        raise NotImplementedError

    def _encrypt_letter(self, p: int, k: int) -> int:
        raise NotImplementedError

    # -- key handling ------------------------------------------------------- #
    def normalise_key(self, key: Any) -> list[int]:
        """Accept a word, a shift list or a dict and return shifts per position."""
        if isinstance(key, dict):
            key = key.get("key") or key.get("shifts")
        if isinstance(key, str):
            key = letters_only(key)
            if not key:
                raise ValueError("key is empty")
            return [A26.index(c) % self.key_alphabet_size for c in key]
        if isinstance(key, int):
            return [key % self.key_alphabet_size]
        return [int(k) % self.key_alphabet_size for k in key]

    def key_word(self, shifts: Iterable[int]) -> str:
        return "".join(A26[s % 26] for s in shifts)

    # -- transforms --------------------------------------------------------- #
    def encrypt(self, plaintext: str, key: Any = "KEY") -> str:
        shifts = self.normalise_key(key)
        span = len(shifts)
        # map_letters keeps case, spaces and punctuation, and counts letters only,
        # so the key advances over letters exactly as it always did.
        return map_letters(
            plaintext, lambda pos, idx: self._encrypt_letter(idx, shifts[pos % span])
        )

    def decrypt(self, ciphertext: str, key: Any = "KEY") -> str:
        shifts = self.normalise_key(key)
        span = len(shifts)
        return map_letters(
            ciphertext, lambda pos, idx: self._decrypt_letter(idx, shifts[pos % span])
        )

    # -- cryptanalysis ------------------------------------------------------ #
    def solve_columns(self, stream: str, key_len: int, ctx: CrackContext) -> list[int]:
        """Chi-squared solve of each of the ``key_len`` Caesar columns."""
        ref = ctx.model.monogram_reference()
        cols = [stream[i::key_len] for i in range(key_len)]
        shifts = []
        for col in cols:
            counts = Counter(A26.index(c) for c in col)
            n = len(col)
            best_s, best_chi = 0, float("inf")
            for s in range(self.key_alphabet_size):
                chi = 0.0
                for v, cnt in counts.items():
                    expected = ref[A26[self._decrypt_letter(v, s)]] * n
                    if expected <= 0:
                        continue
                    chi += (cnt - expected) ** 2 / expected
                if chi < best_chi:
                    best_chi, best_s = chi, s
            shifts.append(best_s)
        return shifts

    def refine_key(self, stream: str, key_len: int, shifts: list[int], ctx: CrackContext) -> list[int]:
        """Coordinate ascent on the key, maximising whole-text quadgram fitness.

        One pass over each key position trying all 26 values; repeat until the
        key stops changing.  Cheap (26 * key_len * passes decryptions) and it
        fixes the per-column errors chi-squared makes on short texts.
        """
        shifts = list(shifts)
        best = self._fitness(stream, shifts, ctx)
        for _ in range(6):
            improved = False
            for pos in range(key_len):
                if ctx.expired():
                    return shifts
                current = shifts[pos]
                for cand in range(self.key_alphabet_size):
                    if cand == current:
                        continue
                    shifts[pos] = cand
                    f = self._fitness(stream, shifts, ctx)
                    if f > best:
                        best, current, improved = f, cand, True
                shifts[pos] = current
            if not improved:
                break
        return shifts

    def _fitness(self, stream: str, shifts: list[int], ctx: CrackContext) -> float:
        n = len(shifts)
        sample = stream[: min(len(stream), 1200)]
        plain = "".join(
            A26[self._decrypt_letter(A26.index(c), shifts[i % n])] for i, c in enumerate(sample)
        )
        return ctx.model.search_fitness(plain)

    def crack(self, ciphertext: str, ctx: CrackContext) -> Iterator[Candidate]:
        stream = self.prepare(ciphertext)
        if len(stream) < self.info.min_length:
            return
        hint_len = ctx.hints.get("key_length")
        hint_key = ctx.hints.get("key")
        if hint_key:
            shifts = self.normalise_key(hint_key)
            plain = self.decrypt(stream, shifts)
            yield ctx.candidate(
                self.name, plain, {"key": self.key_word(shifts)}, steps=ctx.steps, method="hint"
            )
            return
        if hint_len:
            lengths = [(int(hint_len), 1.0, "hint")]
        else:
            lengths = candidate_key_lengths(stream, self.max_key_length)
            if not lengths:
                return
            # IC and Kasiski are unreliable below a few hundred letters: with a
            # dozen letters per column the true period loses the ranking as often
            # as it wins, and the "drop multiples of a shorter period" rule then
            # discards it for good.  Refinement is cheap, so on a short text
            # sweep every admissible period and let the recovered plaintext pick
            # the winner instead of the statistics.
            if len(stream) <= SWEEP_PERIOD_LETTERS:
                known = {k: (q, ev) for k, q, ev in lengths}
                lengths = []
                for k in range(1, self.max_key_length + 1):
                    if k * MIN_LETTERS_PER_COLUMN > len(stream):
                        break
                    q, ev = known.get(k, (0.0, ""))
                    lengths.append((k, q, ev or "exhaustive period sweep"))
        limit = 20 if len(stream) <= SWEEP_PERIOD_LETTERS else 12
        results: list[Candidate] = []
        for key_len, quality, evidence in lengths[:limit]:
            if ctx.expired():
                break
            if key_len * MIN_LETTERS_PER_COLUMN > len(stream):
                continue
            shifts = self.solve_columns(stream, key_len, ctx)
            shifts = self.refine_key(stream, key_len, shifts, ctx)
            plain = self.decrypt(stream, shifts)
            results.append(
                ctx.candidate(
                    self.name,
                    plain,
                    {"key": self.key_word(shifts)},
                    steps=ctx.steps,
                    columns=key_len,
                    key_length=key_len,
                    period_quality=round(quality, 4),
                    evidence=evidence,
                    column_ic=round(ic_of_columns(stream, key_len), 4),
                    method="ic+kasiski, chi-squared columns, quadgram refinement",
                )
            )
        results.sort(key=Candidate.sort_key)
        yield from results

    def likelihood(self, text: str, ctx: CrackContext) -> float:
        stream = self.prepare(text)
        n = len(stream)
        if n < self.info.min_length:
            return 0.0
        ic = index_of_coincidence(stream)
        # Polyalphabetic flattens the distribution: IC drops toward 1/26.
        flat = max(0.0, min(1.0, (ENGLISH_IC - ic) / (ENGLISH_IC - RANDOM_IC)))
        lengths = candidate_key_lengths(stream, self.max_key_length)
        periodic = 0.0
        if lengths:
            k, q, _ = lengths[0]
            if 2 <= k <= self.max_key_length:
                periodic = q
        fit = ctx.model.ngram_score(stream)
        unreadable = max(0.0, min(1.0, (-4.6 - fit) / 1.5))
        return round(0.45 * flat + 0.35 * periodic + 0.20 * unreadable, 4)


class Vigenere(PeriodicCipher):
    """Vigenere: C = P + K (mod 26)."""

    info = CipherInfo(
        name="vigenere",
        title="Vigenère",
        family=Family.POLYALPHABETIC,
        key_type="keyword",
        min_length=24,
        cost=MODERATE,
        aliases=("vig", "vigenere_cipher", "le chiffre indéchiffrable"),
        description="Repeating-key addition. Cracked by period finding (IC + Kasiski) then per-column Caesar solving.",
        example_key="LEMON",
    )

    def _decrypt_letter(self, c: int, k: int) -> int:
        return (c - k) % 26

    def _encrypt_letter(self, p: int, k: int) -> int:
        return (p + k) % 26


class Beaufort(PeriodicCipher):
    """Beaufort: C = K - P (mod 26).  Self-reciprocal."""

    info = CipherInfo(
        name="beaufort",
        title="Beaufort",
        family=Family.POLYALPHABETIC,
        key_type="keyword",
        min_length=24,
        cost=MODERATE,
        description="C = K - P. Reciprocal: encryption and decryption are the same operation.",
        example_key="LEMON",
    )

    def _decrypt_letter(self, c: int, k: int) -> int:
        return (k - c) % 26

    _encrypt_letter = _decrypt_letter


class VariantBeaufort(PeriodicCipher):
    """Variant Beaufort (German): C = P - K (mod 26)."""

    info = CipherInfo(
        name="variant_beaufort",
        title="Variant Beaufort",
        family=Family.POLYALPHABETIC,
        key_type="keyword",
        min_length=24,
        cost=MODERATE,
        aliases=("german", "vigenere_decrypt"),
        description="C = P - K: Vigenere encryption with the decryption rule.",
        example_key="LEMON",
    )

    def _decrypt_letter(self, c: int, k: int) -> int:
        return (c + k) % 26

    def _encrypt_letter(self, p: int, k: int) -> int:
        return (p - k) % 26


class Gronsfeld(PeriodicCipher):
    """Gronsfeld: Vigenere with a numeric key (shifts 0-9 only)."""

    info = CipherInfo(
        name="gronsfeld",
        title="Gronsfeld",
        family=Family.POLYALPHABETIC,
        key_type="digits 0-9",
        min_length=24,
        cost=MODERATE,
        description="Vigenere restricted to a digit key, so each column has only 10 possible shifts.",
        example_key="31415",
    )
    key_alphabet_size = 10

    def _decrypt_letter(self, c: int, k: int) -> int:
        return (c - k) % 26

    def _encrypt_letter(self, p: int, k: int) -> int:
        return (p + k) % 26

    def normalise_key(self, key: Any) -> list[int]:
        if isinstance(key, dict):
            key = key.get("key")
        if isinstance(key, str):
            digits = "".join(ch for ch in key if ch.isdigit())
            if digits:
                return [int(d) for d in digits]
            return [A26.index(c) % 10 for c in letters_only(key)]
        if isinstance(key, int):
            return [int(str(abs(key))[0])]
        return [int(k) % 10 for k in key]

    def key_word(self, shifts: Iterable[int]) -> str:
        return "".join(str(s % 10) for s in shifts)


class Trithemius(PeriodicCipher):
    """Progressive-key cipher: the shift advances by a fixed step each letter.

    Covers the Trithemius cipher (step 1 from A) and every generalisation
    ``key[i] = (start + i*step) mod 26`` -- a 676-key space, so it is brute
    forced exhaustively rather than period-searched.
    """

    info = CipherInfo(
        name="trithemius",
        title="Trithemius / progressive key",
        family=Family.POLYALPHABETIC,
        key_type="(start, step)",
        keyspace=676,
        min_length=16,
        cost=CHEAP,
        aliases=("progressive_key", "progressive"),
        description="Shift increases by a constant step per letter: key[i] = (start + i*step) mod 26.",
        example_key={"start": 0, "step": 1},
    )

    def _shifts(self, key: Any, n: int) -> list[int]:
        if isinstance(key, dict):
            start, step = int(key.get("start", 0)), int(key.get("step", 1))
        else:
            start, step = int(key[0]), int(key[1])
        return [(start + i * step) % 26 for i in range(n)]

    def encrypt(self, plaintext: str, key: Any = (0, 1)) -> str:
        return map_letters(plaintext, lambda pos, idx: idx + self._shift_for_key(key, pos))

    def decrypt(self, ciphertext: str, key: Any = (0, 1)) -> str:
        return map_letters(ciphertext, lambda pos, idx: idx - self._shift_for_key(key, pos))

    def _shift_for_key(self, key: Any, position: int) -> int:
        if isinstance(key, dict):
            start, step = int(key.get("start", 0)), int(key.get("step", 1))
        else:
            start, step = int(key[0]), int(key[1])
        return (start + position * step) % 26

    def keys(self) -> Iterator[tuple[int, int]]:
        for start in range(26):
            # step 0 is a Caesar shift, which Caesar reports better than we can.
            for step in range(1, 26):
                yield (start, step)

    def crack(self, ciphertext: str, ctx: CrackContext) -> Iterator[Candidate]:
        stream = self.prepare(ciphertext)
        if len(stream) < self.info.min_length:
            return
        sample = stream[:1200]
        idx = [A26.index(c) for c in sample]
        results: list[tuple[float, int, int]] = []
        for start in range(26):
            for step in range(1, 26):
                if ctx.expired():
                    return
                plain = "".join(
                    A26[(v - (start + i * step)) % 26] for i, v in enumerate(idx)
                )
                results.append((ctx.model.search_fitness(plain), start, step))
        # Cheap quadgram ranking first; the expensive multi-view score is only
        # worth spending on the leaders of a 676-key sweep.
        results.sort(key=lambda t: -t[0])
        for _, start, step in results[:8]:
            yield ctx.candidate(
                self.name,
                self.decrypt(stream, (start, step)),
                {"start": start, "step": step},
                steps=ctx.steps,
                method="exhaustive 676 keys",
            )


class Autokey(Cipher):
    """Autokey: the key is a short primer followed by the plaintext itself.

    ``C[i] = P[i] + K[i]`` where ``K[i] = primer[i]`` for ``i < m`` and
    ``K[i] = P[i-m]`` afterwards.  That recursion is the weakness: once the
    primer length ``m`` is guessed, the message splits into ``m`` independent
    chains, each fully determined by a single unknown letter.  So the attack is
    ``m`` tiny searches instead of one 26^m search -- chi-squared seeds each
    chain, then coordinate ascent on the primer maximises quadgram fitness.
    """

    info = CipherInfo(
        name="autokey",
        title="Autokey",
        family=Family.POLYALPHABETIC,
        key_type="primer word",
        min_length=40,
        cost=MODERATE,
        aliases=("vigenere_autokey", "auto_key"),
        description="Key = short primer followed by the plaintext itself. Solved by chain decomposition.",
        example_key="QUEEN",
    )
    max_primer = 14

    def normalise_key(self, key: Any) -> list[int]:
        if isinstance(key, dict):
            key = key.get("key") or key.get("primer")
        if isinstance(key, str):
            return [A26.index(c) for c in letters_only(key)]
        return [int(k) % 26 for k in key]

    def encrypt(self, plaintext: str, key: Any = "KEY") -> str:
        return self._run(plaintext, self.normalise_key(key), encrypting=True)

    def decrypt(self, ciphertext: str, key: Any = "KEY") -> str:
        return self._run(ciphertext, self.normalise_key(key), encrypting=False)

    def _run(self, text: str, primer: list[int], *, encrypting: bool) -> str:
        """Autokey with the layout left intact.

        The key stream is the primer followed by the *plaintext* letters, so both
        directions have to track what they have produced so far; non-letters are
        copied through and do not advance the stream.
        """
        m = len(primer)
        plain: list[int] = []
        out: list[str] = []
        for ch in text:
            if not (ch.isascii() and ch.isalpha()):
                out.append(ch)
                continue
            idx = A26.index(ch.upper())
            position = len(plain)
            shift = primer[position] if position < m else plain[position - m]
            value = (idx + shift) % 26 if encrypting else (idx - shift) % 26
            plain.append(idx if encrypting else value)
            letter = A26[value]
            out.append(letter.lower() if ch.islower() else letter)
        return "".join(out)

    def _chains(self, stream: str, m: int) -> list[list[int]]:
        """Chain j holds ciphertext indices j, j+m, j+2m, ..."""
        idx = [A26.index(c) for c in stream]
        return [idx[j::m] for j in range(m)]

    def _solve_chain(self, chain: list[int], m: int, ctx: CrackContext) -> int:
        """Best primer letter for one chain by chi-squared on its plaintext."""
        ref = ctx.model.monogram_reference()
        best_start, best_chi = 0, float("inf")
        for start in range(26):
            plain: list[int] = []
            prev = start
            for k, c in enumerate(chain):
                p = (c - (start if k == 0 else prev)) % 26
                plain.append(p)
                prev = p
            counts = Counter(A26[p] for p in plain)
            n = len(plain)
            chi = sum(
                (counts.get(letter, 0) - ref[letter] * n) ** 2 / (ref[letter] * n)
                for letter in A26
                if ref[letter] > 0
            )
            if chi < best_chi:
                best_chi, best_start = chi, start
        return best_start

    def _decrypt_with_primer(self, stream: str, primer: list[int]) -> str:
        m = len(primer)
        out: list[str] = []
        for i, c in enumerate(stream):
            k = primer[i] if i < m else A26.index(out[i - m])
            out.append(A26[(A26.index(c) - k) % 26])
        return "".join(out)

    def crack(self, ciphertext: str, ctx: CrackContext) -> Iterator[Candidate]:
        stream = self.prepare(ciphertext)
        if len(stream) < self.info.min_length:
            return
        hint = ctx.hints.get("key")
        if hint:
            primer = self.normalise_key(hint)
            yield ctx.candidate(
                self.name,
                self._decrypt_with_primer(stream, primer),
                {"key": "".join(A26[p] for p in primer)},
                steps=ctx.steps,
                method="hint",
            )
            return
        sample = stream[: min(len(stream), 1500)]
        results: list[Candidate] = []
        max_primer = min(self.max_primer, max(1, len(sample) // 8))
        for m in range(1, max_primer + 1):
            if ctx.expired():
                break
            primer = [self._solve_chain(chain, m, ctx) for chain in self._chains(sample, m)]
            # Coordinate ascent over the primer using whole-text fitness.
            best_fit = ctx.model.search_fitness(self._decrypt_with_primer(sample, primer))
            for _ in range(4):
                improved = False
                for pos in range(m):
                    if ctx.expired():
                        break
                    cur = primer[pos]
                    for cand in range(26):
                        if cand == cur:
                            continue
                        primer[pos] = cand
                        fit = ctx.model.search_fitness(self._decrypt_with_primer(sample, primer))
                        if fit > best_fit:
                            best_fit, cur, improved = fit, cand, True
                    primer[pos] = cur
                if not improved:
                    break
            plain = self._decrypt_with_primer(stream, primer)
            results.append(
                ctx.candidate(
                    self.name,
                    plain,
                    {"key": "".join(A26[p] for p in primer)},
                    steps=ctx.steps,
                    columns=m,
                    primer_length=m,
                    method="chain decomposition + quadgram ascent",
                )
            )
        results.sort(key=Candidate.sort_key)
        yield from results

    def likelihood(self, text: str, ctx: CrackContext) -> float:
        stream = self.prepare(text)
        if len(stream) < self.info.min_length:
            return 0.0
        ic = index_of_coincidence(stream)
        flat = max(0.0, min(1.0, (ENGLISH_IC - ic) / (ENGLISH_IC - RANDOM_IC)))
        # Autokey leaks: adjacent letters of plaintext key the next letter, so
        # repeated bigrams at distance 1 are more common than in Vigenere.
        periods = candidate_key_lengths(stream, 12)
        periodic = periods[0][1] if periods else 0.0
        return round(0.6 * flat + 0.4 * (1.0 - periodic), 4)
