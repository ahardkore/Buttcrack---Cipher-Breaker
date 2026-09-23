"""Shift ciphers: Caesar/ROT-N, Atbash, Affine, ROT47 and reversal.

These are the cheap end of the keyspace, and the engine tries them first: a
Caesar answer should arrive in single-digit milliseconds, not after a hill climb.
All of them have small *enumerable* keyspaces, so ``crack`` is exhaustive and
therefore guaranteed to find the key when the cipher really was used.

Identification for this whole family is the index of coincidence: every shift
cipher is monoalphabetic, so it preserves the plaintext's letter distribution
(IC ~ 0.066 for English) while wrecking the n-gram statistics (fitness ~ -7.5).
"High IC + terrible fitness" is the signature, and it is what
:meth:`ShiftCipher.likelihood` measures.
"""

from __future__ import annotations

import string
from typing import Any, Iterator

from ..text import A26, index_of_coincidence, letters_only, printable_only
from .base import CHEAP, Cipher, CipherInfo, CrackContext, Family

# English IC is ~0.0667; random text is ~0.0385.
ENGLISH_IC = 0.0667
RANDOM_IC = 0.0385


def letter_table(mapping: str, alphabet: str = A26) -> dict[int, str]:
    """``str.translate`` table for a letter mapping, covering both cases.

    Translating rather than looping is what makes the exhaustive sweeps cheap,
    and because only letters are in the table, everything else -- spaces, digits,
    punctuation, accents -- passes straight through.  Encrypting prose therefore
    gives prose back instead of a block of capitals.
    """
    table = {ord(c): mapping[i] for i, c in enumerate(alphabet)}
    table.update({ord(c.lower()): mapping[i].lower() for i, c in enumerate(alphabet)})
    return table


def shift_text(text: str, shift: int, alphabet: str = A26) -> str:
    """Shift every character of ``text`` by ``shift`` positions in ``alphabet``."""
    n = len(alphabet)
    shift %= n
    if shift == 0:
        return text
    idx = {c: i for i, c in enumerate(alphabet)}
    return "".join(alphabet[(idx[c] + shift) % n] if c in idx else c for c in text)


class ShiftCipher(Cipher):
    """Shared identification logic for monoalphabetic shift-family ciphers."""

    def prescreen(self, plaintext: str, ctx: CrackContext) -> float:
        """Chi-squared plus a penalty for output that is not mostly letters.

        ROT47 works on printable ASCII, so a wrong shift scatters the message
        across punctuation and digits.  The true shift is the one whose output
        is *almost entirely alphabetic*, and plain chi-squared cannot see that:
        it normalises by the handful of letters that survive.
        """
        stream = self.prepare(plaintext)
        letters = letters_only(stream)
        if not stream:
            return float("inf")
        ratio = len(letters) / len(stream)
        penalty = (1.0 - ratio) * 50.0
        return ctx.model.chi_squared(letters, per_char=True) + penalty

    def likelihood(self, text: str, ctx: CrackContext) -> float:
        stream = self.prepare(text)
        if len(stream) < self.info.min_length:
            return 0.0
        ic = index_of_coincidence(stream)
        # Monoalphabetic ciphers preserve IC; polyalphabetic and transposition do not.
        ic_fit = max(0.0, min(1.0, (ic - RANDOM_IC) / (ENGLISH_IC - RANDOM_IC)))
        fit = ctx.model.ngram_score(stream)
        # ...but only worth ranking highly if the text is *not* already readable.
        unreadable = max(0.0, min(1.0, (-4.6 - fit) / 1.5))
        return round(0.75 * ic_fit + 0.25 * unreadable, 4)


class Caesar(ShiftCipher):
    """Caesar / ROT-N: every letter shifted by a fixed amount."""

    info = CipherInfo(
        name="caesar",
        title="Caesar (ROT-N)",
        family=Family.SHIFT,
        key_type="shift 0-25",
        keyspace=26,
        min_length=2,
        cost=CHEAP,
        aliases=("rot", "rotn", "rot-n", "shift", "caesar_cipher"),
        description="Each letter is shifted by a fixed number of places. ROT13 is shift 13.",
        example_key=7,
    )

    def encrypt(self, plaintext: str, key: Any = 3) -> str:
        shift = int(key) % 26
        return plaintext.translate(letter_table(A26[shift:] + A26[:shift]))

    def decrypt(self, ciphertext: str, key: Any = 3) -> str:
        shift = (-int(key)) % 26
        return ciphertext.translate(letter_table(A26[shift:] + A26[:shift]))

    def keys(self) -> Iterator[int]:
        # Shift 0 is the identity: reporting it as "Caesar with key 0" would
        # steal credit from the honest answer, which is "no cipher".
        yield from range(1, 26)

    # crack() is inherited: 26 keys is small enough to sweep exhaustively, and
    # the base-class chi-squared prescreen already ranks Caesar shifts correctly.


class ROT13(Caesar):
    """ROT13: Caesar with a fixed shift of 13 -- its own inverse.

    Registered separately from :class:`Caesar` because everybody asks for it by
    name, and because a keyless involution deserves keyless reporting: when the
    answer is shift 13 the pool's tie-break prefers this candidate, whose key is
    ``None`` rather than ``13``.
    """

    info = CipherInfo(
        name="rot13",
        title="ROT13",
        family=Family.SHIFT,
        keyed=False,
        key_type="none (fixed shift of 13)",
        keyspace=1,
        min_length=2,
        cost=CHEAP,
        aliases=("rot-13", "rot_13", "rotate13"),
        description="Caesar shift of 13. Applying it twice returns the original text.",
    )

    def encrypt(self, plaintext: str, key: Any = None) -> str:
        return plaintext.translate(letter_table(A26[13:] + A26[:13]))

    decrypt = encrypt  # ROT13 is an involution

    def keys(self) -> Iterator[None]:
        yield None


class Atbash(ShiftCipher):
    """Atbash: the alphabet reversed (A<->Z, B<->Y).  Keyless."""

    info = CipherInfo(
        name="atbash",
        title="Atbash",
        family=Family.SHIFT,
        keyed=False,
        key_type="none",
        keyspace=1,
        min_length=2,
        cost=CHEAP,
        description="Hebrew substitution cipher mapping the alphabet onto its reverse.",
    )

    _TABLE = str.maketrans(A26, A26[::-1])

    _DECODE = letter_table(A26[::-1])

    def encrypt(self, plaintext: str, key: Any = None) -> str:
        return plaintext.translate(self._DECODE)

    decrypt = encrypt  # Atbash is an involution

    def keys(self) -> Iterator[None]:
        yield None

    def crack(self, ciphertext: str, ctx: CrackContext) -> Iterator[Candidate]:
        stream = self.prepare(ciphertext)
        if not stream:
            return
        yield ctx.candidate(self.name, stream.translate(self._TABLE), None, steps=ctx.steps)


class Affine(ShiftCipher):
    """Affine: E(x) = (a*x + b) mod 26 with ``a`` coprime to 26 (312 keys)."""

    info = CipherInfo(
        name="affine",
        title="Affine",
        family=Family.SHIFT,
        key_type="(a, b) pair",
        keyspace=312,
        min_length=4,
        cost=CHEAP,
        description="Linear map x -> a*x + b mod 26. Caesar is the special case a=1.",
        example_key={"a": 5, "b": 8},
    )

    UNITS = (1, 3, 5, 7, 9, 11, 15, 17, 19, 21, 23, 25)

    @staticmethod
    def _inverse(a: int) -> int:
        return pow(a, -1, 26)

    def encrypt(self, plaintext: str, key: Any = (5, 8)) -> str:
        a, b = self._ab(key)
        # One 52-entry table per key, then a single translate: the sweep runs this
        # 286 times over the whole ciphertext, and case and punctuation survive.
        table = letter_table("".join(A26[(a * x + b) % 26] for x in range(26)))
        return plaintext.translate(table)

    def decrypt(self, ciphertext: str, key: Any = (5, 8)) -> str:
        a, b = self._ab(key)
        inv = self._inverse(a)
        table = letter_table("".join(A26[(inv * (y - b)) % 26] for y in range(26)))
        return ciphertext.translate(table)

    def _ab(self, key: Any) -> tuple[int, int]:
        if isinstance(key, dict):
            return int(key.get("a", 1)), int(key.get("b", 0))
        a, b = key
        if a % 26 not in self.UNITS:
            raise ValueError(f"a={a} has no inverse mod 26; must be one of {self.UNITS}")
        return a % 26, b % 26

    def keys(self) -> Iterator[tuple[int, int]]:
        for a in self.UNITS:
            # a == 1 is Caesar, which is reported by its own cipher; the
            # identity (1, 0) is reported as "no cipher".
            if a == 1:
                continue
            for b in range(26):
                yield (a, b)

    # crack() is inherited: 312 keys swept exhaustively.


class ROT47(ShiftCipher):
    """ROT47: Caesar over all 94 printable ASCII characters (case, digits, punctuation)."""

    info = CipherInfo(
        name="rot47",
        title="ROT47",
        family=Family.SHIFT,
        key_type="shift 0-93",
        keyspace=94,
        min_length=4,
        cost=CHEAP,
        alphabet=string.printable[:94],
        description="Rotates printable ASCII (0x21-0x7e) by 47 places. Preserves case and digits.",
        example_key=47,
    )
    BASE = 0x21
    SIZE = 94

    def prepare(self, text: str) -> str:
        return printable_only(text).strip()

    def _rot(self, text: str, n: int) -> str:
        out = []
        for ch in text:
            o = ord(ch)
            if self.BASE <= o < self.BASE + self.SIZE:
                out.append(chr(self.BASE + (o - self.BASE + n) % self.SIZE))
            else:
                out.append(ch)
        return "".join(out)

    def encrypt(self, plaintext: str, key: Any = 47) -> str:
        return self._rot(self.prepare(plaintext), int(key))

    def decrypt(self, ciphertext: str, key: Any = 47) -> str:
        return self._rot(self.prepare(ciphertext), -int(key))

    def keys(self) -> Iterator[int]:
        yield from range(1, self.SIZE)

    def prescreen(self, plaintext: str, ctx: CrackContext) -> float:
        """Lower is better: quadgram fitness, with a letter-ratio penalty.

        A wrong ROT47 shift scatters the message across punctuation and digits,
        which the ratio penalty catches -- but the shift exactly 32 places from
        the correct one is a trap: 32 is the ASCII case difference, so that
        reading is the *same message* in the other case, with every comma turned
        into a stray letter.  It has a higher letter ratio than the truth, so a
        ratio-led test prefers it and the answer comes back as
        ``MANUSCRIPTSj THREE``.  Quadgrams see the stray letters and rank the
        real key first.
        """
        stream = self.prepare(plaintext)
        if not stream:
            return float("inf")
        letters = letters_only(stream)
        if not letters:
            return float("inf")
        penalty = (1.0 - len(letters) / len(stream)) * 6.0
        return -ctx.model.search_fitness(letters) + penalty

    def likelihood(self, text: str, ctx: CrackContext) -> float:
        stream = self.prepare(text)
        if len(stream) < self.info.min_length:
            return 0.0
        # ROT47 maps lowercase letters into punctuation/digit ranges, so a high
        # ratio of non-alphabetic printable characters is the tell.
        alnum = sum(c.isalnum() for c in stream)
        weird = sum(33 <= ord(c) <= 126 and not c.isalnum() and c not in " .,;:'\"!?-" for c in stream)
        return round(min(1.0, weird / max(len(stream), 1) * 2.5), 4) if weird > alnum * 0.2 else 0.05


class Reverse(ShiftCipher):
    """Reversal: the whole message written backwards.

    Conceptually a layer, but deliberately *not* a :class:`LayerCipher`:
    reversal "decodes" any text at all, so the recursive peeler would try it at
    every node and double the search tree for no gain.  It is attacked instead,
    which costs one key.
    """

    info = CipherInfo(
        name="reverse",
        title="Reverse",
        family=Family.SHIFT,
        keyed=False,
        key_type="none",
        keyspace=1,
        min_length=2,
        cost=CHEAP,
        layer=False,
        description="The message reversed. Often layered under or over other ciphers.",
    )

    def encrypt(self, plaintext: str, key: Any = None) -> str:
        return plaintext.strip()[::-1]

    decrypt = encrypt

    def keys(self) -> Iterator[None]:
        yield None

    def crack(self, ciphertext: str, ctx: CrackContext) -> Iterator[Candidate]:
        stream = ciphertext.strip()
        if not stream:
            return
        yield ctx.candidate(self.name, stream[::-1], None, steps=ctx.steps)
