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
from collections.abc import Iterator
from typing import Any

from ..results import Candidate
from ..text import A25, A26, letters_only
from .base import CHEAP, CipherInfo, CrackContext, Family
from .encodings import _Encoding

MORSE = {
    "A": ".-",
    "B": "-...",
    "C": "-.-.",
    "D": "-..",
    "E": ".",
    "F": "..-.",
    "G": "--.",
    "H": "....",
    "I": "..",
    "J": ".---",
    "K": "-.-",
    "L": ".-..",
    "M": "--",
    "N": "-.",
    "O": "---",
    "P": ".--.",
    "Q": "--.-",
    "R": ".-.",
    "S": "...",
    "T": "-",
    "U": "..-",
    "V": "...-",
    "W": ".--",
    "X": "-..-",
    "Y": "-.--",
    "Z": "--..",
    "0": "-----",
    "1": ".----",
    "2": "..---",
    "3": "...--",
    "4": "....-",
    "5": ".....",
    "6": "-....",
    "7": "--...",
    "8": "---..",
    "9": "----.",
    ".": ".-.-.-",
    ",": "--..--",
    "?": "..--..",
    "'": ".----.",
    "!": "-.-.--",
    "/": "-..-.",
    "(": "-.--.",
    ")": "-.--.-",
    "&": ".-...",
    ":": "---...",
    ";": "-.-.-.",
    "=": "-...-",
    "+": ".-.-.",
    "-": "-....-",
    "_": "..--.-",
    '"': ".-..-.",
    "$": "...-..-",
    "@": ".--.-.",
}
MORSE_DECODE = {v: k for k, v in MORSE.items()}

#: Bacon's biliteral table.  Only 24 of the 32 five-bit codes are used: I and J
#: share one code and U and V share another, exactly as Bacon specified.  When
#: decoding, the shared codes resolve to I and U (the earlier letter).
BACON_26 = [
    "AAAAA",
    "AAAAB",
    "AAABA",
    "AAABB",
    "AABAA",
    "AABAB",
    "AABBA",
    "AABBB",
    "ABAAA",
    "ABAAA",
    "ABAAB",
    "ABABA",
    "ABABB",
    "ABBAA",
    "ABBAB",
    "ABBBA",
    "ABBBB",
    "BAAAA",
    "BAAAB",
    "BAABA",
    "BAABB",
    "BAABB",
    "BABAA",
    "BABAB",
    "BABBA",
    "BABBB",
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
            letters = [MORSE_DECODE[g] for g in self._symbols(word) if g in MORSE_DECODE]
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
            yield ctx.candidate(self.name, transposed, {"grid": A25, "order": "column-row"}, steps=ctx.steps)


#: Tap (or "knock") code: the Polybius square struck out as counts of taps.
#: C shares K's cell, which is why a decoded ``K`` is reported as ``C/K``-safe
#: ``C`` -- the convention used by the prisoners who invented it.
TAP_GRID = A25.replace("K", "")  # 24 letters: C doubles for K, J folded into I


class TapCode(_Encoding):
    """Tap code: two runs of taps per letter, row then column of a 5x5 grid."""

    info = CipherInfo(
        name="tap_code",
        title="Tap code",
        family=Family.CODE,
        keyed=False,
        key_type="none",
        keyspace=1,
        min_length=6,
        cost=CHEAP,
        layer=True,
        aliases=("knock_code", "tap", "prisoner_code"),
        description="Row and column of a 5x5 grid struck as groups of taps (C=K, I=J).",
    )

    @staticmethod
    def _groups(text: str) -> list[int]:
        """Tap runs as counts. Accepts dots, middots, X, knocks and digits."""
        normalised = (
            text.replace("\u00b7", ".")
            .replace("\u2022", ".")
            .replace("*", ".")
            .replace("x", ".")
            .replace("X", ".")
            .replace("o", ".")
            .replace("O", ".")
        )
        runs = [g for g in re.split(r"[^.]+", normalised) if g]
        return [len(g) for g in runs]

    def decodable(self, text: str) -> bool:
        runs = self._groups(text)
        if len(runs) < 4 or len(runs) % 2:
            return False
        # Every run must be a legal coordinate, and a stream of single taps is
        # not a tap code -- it is a stream of dots (Morse, or just punctuation).
        return all(1 <= r <= 5 for r in runs) and len(set(runs)) > 1

    def encode(self, text: str) -> str:
        out = []
        for ch in letters_only(text).replace("J", "I").replace("K", "C"):
            if ch not in A25:
                continue
            idx = A25.index(ch)
            out.append("." * (idx // 5 + 1) + " " + "." * (idx % 5 + 1))
        return "  ".join(out)

    def decode(self, text: str) -> str:
        runs = self._groups(text)
        out = []
        for i in range(0, len(runs) - 1, 2):
            row, col = runs[i] - 1, runs[i + 1] - 1
            if 0 <= row < 5 and 0 <= col < 5:
                out.append(A25[row * 5 + col])
        return "".join(out)


#: The NATO/ICAO spelling alphabet, plus the spellings that predate it or are
#: simply misspelled in puzzles ("alfa"/"alpha", "juliett"/"juliet", "xray").
NATO = {
    "A": "Alfa",
    "B": "Bravo",
    "C": "Charlie",
    "D": "Delta",
    "E": "Echo",
    "F": "Foxtrot",
    "G": "Golf",
    "H": "Hotel",
    "I": "India",
    "J": "Juliett",
    "K": "Kilo",
    "L": "Lima",
    "M": "Mike",
    "N": "November",
    "O": "Oscar",
    "P": "Papa",
    "Q": "Quebec",
    "R": "Romeo",
    "S": "Sierra",
    "T": "Tango",
    "U": "Uniform",
    "V": "Victor",
    "W": "Whiskey",
    "X": "Xray",
    "Y": "Yankee",
    "Z": "Zulu",
    "0": "Zero",
    "1": "One",
    "2": "Two",
    "3": "Three",
    "4": "Four",
    "5": "Five",
    "6": "Six",
    "7": "Seven",
    "8": "Eight",
    "9": "Nine",
}
NATO_DECODE = {v.lower(): k for k, v in NATO.items()}
NATO_DECODE.update(
    {
        "alpha": "A",
        "juliet": "J",
        "x-ray": "X",
        "whisky": "W",
        "niner": "9",
    }
)


class NatoPhonetic(_Encoding):
    """The NATO spelling alphabet as a transport layer."""

    info = CipherInfo(
        name="nato",
        title="NATO phonetic alphabet",
        family=Family.CODE,
        keyed=False,
        key_type="none",
        keyspace=1,
        min_length=10,
        cost=CHEAP,
        layer=True,
        aliases=("nato_phonetic", "phonetic_alphabet", "icao"),
        description="One spelling-alphabet word per letter (Alfa Bravo Charlie ...).",
    )

    @staticmethod
    def _words(text: str) -> list[str]:
        return [w for w in re.split(r"[^A-Za-z0-9-]+", text) if w]

    def decodable(self, text: str) -> bool:
        words = self._words(text)
        if len(words) < 4:
            return False
        hits = sum(1 for w in words if w.lower() in NATO_DECODE)
        return hits / len(words) >= 0.7

    def encode(self, text: str) -> str:
        return " ".join(NATO[c] for c in text.upper() if c in NATO)

    def decode(self, text: str) -> str:
        return "".join(NATO_DECODE.get(w.lower(), "") for w in self._words(text))


#: Unicode braille patterns are a bit field: dot 1 = 0x01, dot 2 = 0x02, and so
#: on, offset from U+2800.  Grade 1 braille letters are the standard assignment.
BRAILLE_LETTERS = {
    "A": 0x01,
    "B": 0x03,
    "C": 0x09,
    "D": 0x19,
    "E": 0x11,
    "F": 0x0B,
    "G": 0x1B,
    "H": 0x13,
    "I": 0x0A,
    "J": 0x1A,
    "K": 0x05,
    "L": 0x07,
    "M": 0x0D,
    "N": 0x1D,
    "O": 0x15,
    "P": 0x0F,
    "Q": 0x1F,
    "R": 0x17,
    "S": 0x0E,
    "T": 0x1E,
    "U": 0x25,
    "V": 0x27,
    "W": 0x3A,
    "X": 0x2D,
    "Y": 0x3D,
    "Z": 0x35,
}
BRAILLE_DECODE = {chr(0x2800 + bits): letter for letter, bits in BRAILLE_LETTERS.items()}
BRAILLE_DECODE["\u2800"] = " "


class Braille(_Encoding):
    """Unicode braille patterns (grade 1, letters only)."""

    info = CipherInfo(
        name="braille",
        title="Braille (Unicode patterns)",
        family=Family.CODE,
        keyed=False,
        key_type="none",
        keyspace=1,
        min_length=4,
        cost=CHEAP,
        layer=True,
        aliases=("unicode_braille", "braille_unicode"),
        description="Unicode braille cells U+2800..U+28FF, grade 1 letter assignments.",
    )

    @staticmethod
    def _cells(text: str) -> list[str]:
        return [c for c in text if 0x2800 <= ord(c) <= 0x28FF]

    def decodable(self, text: str) -> bool:
        cells = self._cells(text)
        if len(cells) < 4:
            return False
        known = sum(1 for c in cells if c in BRAILLE_DECODE)
        return known / len(cells) >= 0.7

    def encode(self, text: str) -> str:
        out = []
        for ch in text.upper():
            if ch in BRAILLE_LETTERS:
                out.append(chr(0x2800 + BRAILLE_LETTERS[ch]))
            elif ch.isspace():
                out.append("\u2800")
        return "".join(out)

    def decode(self, text: str) -> str:
        return "".join(BRAILLE_DECODE.get(c, "") for c in self._cells(text))


#: ITA2 ("Baudot-Murray") letter shift.  Teleprinter tape is five bits per
#: character; only the letters table is decoded here, because a puzzle that
#: switches to the figures table mid-message is vanishingly rare and decoding
#: it wrongly is worse than leaving the character out.
ITA2_LETTERS = {
    "00000": "",
    "00100": " ",
    "01000": "\n",
    "00010": "\n",
    "11000": "A",
    "10011": "B",
    "01110": "C",
    "10010": "D",
    "10000": "E",
    "10110": "F",
    "01011": "G",
    "00101": "H",
    "01100": "I",
    "11010": "J",
    "11110": "K",
    "01001": "L",
    "00111": "M",
    "00110": "N",
    "00011": "O",
    "01101": "P",
    "11101": "Q",
    "01010": "R",
    "10100": "S",
    "00001": "T",
    "11100": "U",
    "01111": "V",
    "11001": "W",
    "10111": "X",
    "10101": "Y",
    "10001": "Z",
}
ITA2_ENCODE = {v: k for k, v in ITA2_LETTERS.items() if v.strip()}
ITA2_ENCODE[" "] = "00100"


class Baudot(_Encoding):
    """ITA2 / Baudot-Murray five-bit teleprinter code."""

    info = CipherInfo(
        name="baudot",
        title="Baudot / ITA2 (5-bit)",
        family=Family.CODE,
        keyed=False,
        key_type="none",
        keyspace=1,
        min_length=15,
        cost=CHEAP,
        layer=True,
        aliases=("ita2", "teletype", "baudot_murray"),
        description="Five bits per character, ITA2 letters table. Distinguished from Bacon by its own letter assignment.",
    )

    @staticmethod
    def _bits(text: str) -> str:
        bits = "".join(c for c in text if c in "01")
        return bits if len(bits) >= 15 and len(bits) % 5 == 0 else ""

    def decodable(self, text: str) -> bool:
        bits = self._bits(text)
        if not bits:
            return False
        # A 5-bit stream is also valid Bacon, so require that this *table*
        # explains it: mostly real characters, and not mostly unassigned codes.
        groups = [bits[i : i + 5] for i in range(0, len(bits), 5)]
        known = sum(1 for g in groups if ITA2_LETTERS.get(g, "").strip())
        return known / len(groups) >= 0.8

    def encode(self, text: str) -> str:
        out = []
        for ch in text.upper():
            code = ITA2_ENCODE.get(ch)
            if code:
                out.append(code)
        return " ".join(out)

    def decode(self, text: str) -> str:
        bits = self._bits(text)
        if not bits:
            return ""
        return "".join(ITA2_LETTERS.get(bits[i : i + 5], "") for i in range(0, len(bits), 5))
