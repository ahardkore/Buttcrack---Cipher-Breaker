"""Letter/number codes: Morse, Bacon, A1Z26 and the Polybius square.

These sit between ciphers and encodings: they are keyed only by convention, but
they change the *character set* completely, so they are the layers most often
wrapped around a real cipher (``base64(morse(vigenere(...)))``).

Each implements :meth:`decodable` so the engine can recognise the format from
the shape of the input alone -- Morse from its dot/dash alphabet, Bacon from a
two-symbol stream in groups of five, A1Z26 from numbers in 1..26, Polybius from
digit pairs in 1..5.

Bacon gets two variants because both appear in the wild: an explicit two-symbol
alphabet (``aabbab``... or ``01001``...) and the steganographic case variant
where uppercase and lowercase letters of ordinary-looking text carry the bits.
"""

from __future__ import annotations

import re
from typing import Any, Iterator

from ..results import Candidate
from ..text import A25, A26, letters_only
from .base import CHEAP, CipherInfo, CrackContext, Family, LayerCipher
from .encodings import _Encoding

MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.",
    "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
    "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
    "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
    "Y": "-.--", "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
    "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.",
    ".": ".-.-.-", ",": "--..--", "?": "..--..", "'": ".----.", "!": "-.-.--",
    "/": "-..-.", "(": "-.--.", ")": "-.--.-", "&": ".-...", ":": "---...",
    ";": "-.-.-.", "=": "-...-", "+": ".-.-.", "-": "-....-", "_": "..--.-",
    '"': ".-..-.", "$": "...-..-", "@": ".--.-.",
}
MORSE_DECODE = {v: k for k, v in MORSE.items()}

#: Bacon's biliteral table.  Only 24 of the 32 five-bit codes are used: I and J
#: share one code and U and V share another, exactly as Bacon specified.  When
#: decoding, the shared codes resolve to I and U (the earlier letter).
BACON_26 = [
    "AAAAA", "AAAAB", "AAABA", "AAABB", "AABAA", "AABAB", "AABBA", "AABBB",
    "ABAAA", "ABAAA", "ABAAB", "ABABA", "ABABB", "ABBAA", "ABBAB", "ABBBA",
    "ABBBB", "BAAAA", "BAAAB", "BAABA", "BAABB", "BAABB", "BABAA", "BABAB",
    "BABBA", "BABBB",
]


def bacon_bits(letters: str) -> str:
    """Encode A-Z letters into Bacon's five-bit ``ab`` stream."""
    return "".join(BACON_26[A26.index(c)].replace("A", "a").replace("B", "b") for c in letters)


def decode_bacon_bits(bits: str) -> str:
    """Decode an ``ab`` stream.  Shared codes resolve to the earlier letter."""
    table: dict[str, str] = {}
    for letter, pattern in zip(A26, BACON_26):
        # First writer wins, so the shared I/J and U/V codes resolve to I and U.
        table.setdefault(pattern.replace("A", "a").replace("B", "b"), letter)
    out = []
    for i in range(0, len(bits) - 4, 5):
        out.append(table.get(bits[i : i + 5], "?"))
    return "".join(out)


class Morse(_Encoding):
    """International Morse code."""

    info = CipherInfo(
        name="morse",
        title="Morse code",
        family=Family.CODE,
        keyed=False,
        key_type="none",
        keyspace=1,
        min_length=4,
        cost=CHEAP,
        layer=True,
        aliases=("morse_code", "dots_and_dashes"),
        description="Dots and dashes per letter; spaces between letters, ' / ' between words.",
    )

    @staticmethod
    def _symbols(text: str) -> list[str]:
        """Split into letter groups, accepting the usual separator styles."""
        normalised = text.replace("\u2013", "-").replace("\u2014", "-").replace("\u00b7", ".")
        normalised = normalised.replace("_", "-").replace("0", "-").replace("1", ".")
        return [g for g in re.split(r"[\s,;|/]+", normalised.strip()) if g]

    def decodable(self, text: str) -> bool:
        groups = self._symbols(text)
        if len(groups) < 3:
            return False
        allowed = set(".-/")
        if not all(set(g) <= allowed for g in groups):
            return False
        return sum(1 for g in groups if g in MORSE_DECODE) / len(groups) >= 0.6

    def encode(self, text: str) -> str:
        out = []
        for word in text.split():
            out.append(" ".join(MORSE.get(c.upper(), "") for c in word if c.upper() in MORSE))
        return " / ".join(o for o in out if o)

    def decode(self, text: str) -> str:
        words = []
        for word in text.split("/"):
            letters = [
                MORSE_DECODE[g] for g in self._symbols(word) if g in MORSE_DECODE
            ]
            if letters:
                words.append("".join(letters))
        return " ".join(words)


class Bacon(_Encoding):
    """Bacon's biliteral cipher (two-symbol 5-bit encoding)."""

    info = CipherInfo(
        name="bacon",
        title="Bacon cipher",
        family=Family.CODE,
        keyed=False,
        key_type="none",
        keyspace=2,
        min_length=10,
        cost=CHEAP,
        layer=True,
        aliases=("biliteral", "bacons_cipher"),
        description="Five symbols per letter over a two-letter alphabet. Both the 24-letter (I=J, U=V) and 26-letter tables are tried.",
    )

    @staticmethod
    def _bits(text: str) -> str:
        """Reduce any two-symbol stream to ``ab``."""
        chars = [c for c in text if not c.isspace()]
        distinct = sorted(set(chars))
        if len(distinct) != 2:
            return ""
        low, high = distinct
        return "".join("a" if c == low else "b" for c in chars)

    def decodable(self, text: str) -> bool:
        bits = self._bits(text)
        return bool(bits) and len(bits) >= 10 and len(bits) % 5 == 0

    def encode(self, text: str) -> str:
        out = []
        for ch in letters_only(text):
            idx = A26.index(ch)
            out.append(BACON_26[idx].replace("A", "a").replace("B", "b"))
        return " ".join(out)

    def decode(self, text: str) -> str:
        bits = self._bits(text)
        if not bits:
            return ""
        return decode_bacon_bits(bits)

    def crack(self, ciphertext: str, ctx: CrackContext) -> Iterator[Candidate]:
        if not self.decodable(ciphertext):
            return
        out = self.decode(ciphertext)
        if out:
            yield ctx.candidate(self.name, out, {"alphabet": "26 (I/J, U/V distinct)"}, steps=ctx.steps)


class BaconCase(_Encoding):
    """Bacon's steganographic variant: letter *case* carries the bits.

    A message that looks like ordinary mixed-case prose can hide a biliteral
    payload where uppercase = ``a`` and lowercase = ``b``.  Detection is the
    interesting part: it needs a mixed-case alphabetic run whose length is a
    multiple of five and whose decoding reads as English.
    """

    info = CipherInfo(
        name="bacon_case",
        title="Bacon (letter case)",
        family=Family.CODE,
        keyed=False,
        key_type="none",
        keyspace=2,
        min_length=20,
        cost=CHEAP,
        layer=True,
        aliases=("bacon_steganography", "case_bacon"),
        description="Uppercase/lowercase of ordinary text encodes Bacon's five-bit letters.",
    )

    @staticmethod
    def _bits(text: str) -> str:
        return "".join("a" if c.isupper() else "b" for c in text if c.isalpha() and c.isascii())

    def decodable(self, text: str) -> bool:
        bits = self._bits(text)
        if len(bits) < 20 or len(bits) % 5:
            return False
        # Mixed case is required, and a long run of one case means it is prose.
        return 0.1 < sum(c == "a" for c in bits) / len(bits) < 0.9

    #: Ordinary-looking text whose letter cases carry the payload.
    COVER = (
        "the railway station at ashford was crowded with travellers waiting for the "
        "delayed express and the station master walked up and down the platform "
        "muttering about the weather and the shortage of coal in the winter months"
    )

    def encode(self, text: str) -> str:
        bits = bacon_bits(letters_only(text))
        cover = self.COVER
        while sum(c.isalpha() for c in cover) < len(bits):
            cover = cover + " " + cover
        out = []
        bit_index = 0
        for ch in cover:
            if ch.isalpha() and bit_index < len(bits):
                out.append(ch.upper() if bits[bit_index] == "a" else ch)
                bit_index += 1
            else:
                out.append(ch)
            if bit_index >= len(bits):
                break
        return "".join(out)

    def decode(self, text: str) -> str:
        return decode_bacon_bits(self._bits(text))


class A1Z26(_Encoding):
    """A1Z26: letters numbered 1-26."""

    info = CipherInfo(
        name="a1z26",
        title="A1Z26 (numbered alphabet)",
        family=Family.CODE,
        keyed=False,
        key_type="none",
        keyspace=1,
        min_length=4,
        cost=CHEAP,
        layer=True,
        aliases=("numbers", "letter_numbers", "n1z26"),
        description="Each letter replaced by its position in the alphabet, separated by spaces or dashes.",
    )

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return [t for t in re.split(r"[\s,;|/_-]+", text.strip()) if t]

    def decodable(self, text: str) -> bool:
        tokens = self._tokens(text)
        if len(tokens) < 3:
            return False
        if not all(t.isdigit() for t in tokens):
            return False
        values = [int(t) for t in tokens]
        if not all(1 <= v <= 26 for v in values):
            return False
        # Distinguish from decimal ASCII: A1Z26 has plenty of small values and
        # an average near 13 rather than near 100.
        return sum(values) / len(values) < 30

    def encode(self, text: str) -> str:
        return " ".join(str(A26.index(c) + 1) for c in letters_only(text))

    def decode(self, text: str) -> str:
        out = []
        for token in self._tokens(text):
            if not token.isdigit():
                continue
            value = int(token)
            out.append(A26[value - 1] if 1 <= value <= 26 else "?")
        return "".join(out)


class Polybius(_Encoding):
    """Polybius square: each letter as its (row, column) coordinates."""

    info = CipherInfo(
        name="polybius",
        title="Polybius square",
        family=Family.CODE,
        key_type="keyword (optional)",
        keyspace=2,
        min_length=6,
        cost=CHEAP,
        layer=True,
        aliases=("polybius_square", "grid_cipher"),
        example_key="MONARCHY",
        description="5x5 coordinate grid (I/J merged). Both digit pairs and tap-code style separators are accepted.",
    )

    def prepare(self, text: str) -> str:
        return text.strip()

    @staticmethod
    def _digits(text: str) -> str:
        return "".join(c for c in text if c.isdigit())

    def decodable(self, text: str) -> bool:
        digits = self._digits(text)
        return len(digits) >= 6 and len(digits) % 2 == 0 and all(c in "12345" for c in digits)

    def _grid(self, key: Any = None) -> str:
        if not key:
            return A25
        from .polygraphic import make_grid

        return make_grid(str(key))

    def encode(self, text: str, key: Any = None) -> str:
        grid = self._grid(key)
        out = []
        for ch in letters_only(text).replace("J", "I"):
            idx = grid.index(ch)
            out.append(f"{idx // 5 + 1}{idx % 5 + 1}")
        return " ".join(out)

    def decrypt(self, ciphertext: str, key: Any = None) -> str:
        return self.decode(ciphertext, key)

    def encrypt(self, plaintext: str, key: Any = None) -> str:
        return self.encode(plaintext, key)

    def decode(self, text: str, key: Any = None) -> str:
        grid = self._grid(key)
        digits = self._digits(text)
        out = []
        for i in range(0, len(digits) - 1, 2):
            row, col = int(digits[i]) - 1, int(digits[i + 1]) - 1
            if 0 <= row < 5 and 0 <= col < 5:
                out.append(grid[row * 5 + col])
            else:
                out.append("?")
        return "".join(out)

    def crack(self, ciphertext: str, ctx: CrackContext) -> Iterator[Candidate]:
        if not self.decodable(ciphertext):
            return
        digits = self._digits(ciphertext)
        # Row-major is the convention, but column-major grids appear often enough
        # that both are worth scoring.
        standard = self.decode(ciphertext)
        if standard:
            yield ctx.candidate(self.name, standard, {"grid": A25, "order": "row-column"}, steps=ctx.steps)
        transposed = "".join(
            A25[(int(digits[i + 1]) - 1) * 5 + (int(digits[i]) - 1)]
            for i in range(0, len(digits) - 1, 2)
            if digits[i] in "12345" and digits[i + 1] in "12345"
        )
        if transposed:
            yield ctx.candidate(
                self.name, transposed, {"grid": A25, "order": "column-row"}, steps=ctx.steps
            )
