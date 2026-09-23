"""Text normalisation and alphabet utilities.

Cryptanalysis lives or dies on getting the *representation* right: a Vigenere
attack on text that still contains digits and newlines silently fails.  This
module centralises every text transform the engine uses so ciphers can agree on
a single normal form.
"""

from __future__ import annotations

import re
import string
from collections import Counter
from typing import Callable

#: The classical alphabet: everything a mono-/poly-alphabetic cipher touches.
A26 = string.ascii_uppercase
A25 = A26.replace("J", "")  # Playfair / Polybius drop J (or merge it with I)
A62 = string.ascii_letters + string.digits
A85 = "".join(chr(c) for c in range(33, 118)) + "z"  # ASCII85 payload alphabet
PRINTABLE = "".join(chr(c) for c in range(32, 127))

_UPPER_ONLY = re.compile(r"[^A-Z]")
_NON_ALNUM = re.compile(r"[^A-Za-z0-9]")
_NON_PRINTABLE = re.compile(r"[^\x20-\x7e]")
_WS = re.compile(r"\s+")


def upper(text: str) -> str:
    """Uppercase ASCII (non-ASCII is left alone; see :func:`fold`)."""
    return text.upper()


def letters_only(text: str, alphabet: str = A26) -> str:
    """Keep only characters in ``alphabet``; the classical normal form.

    >>> letters_only("Attack at dawn, 0600!")
    'ATTACKATDAWN'
    """
    keep = set(alphabet)
    return "".join(c for c in text.upper() if c in keep)


def alnum_only(text: str) -> str:
    """Keep letters and digits, discard everything else (case preserved)."""
    return _NON_ALNUM.sub("", text)


def printable_only(text: str) -> str:
    """Keep ASCII 0x20-0x7e (the normal form for XOR / byte attacks)."""
    return _NON_PRINTABLE.sub("", text)


#: Whitespace that is safe to trim from a ciphertext or a peeled payload.
#: Python's default ``str.strip()`` is *not* safe here: it also treats 0x1c-0x1f
#: (the ASCII separators) as whitespace, and those are ordinary payload bytes for
#: XOR-style attacks.  Trimming them silently deletes message characters -- a
#: leading 0x1f costs you the first letter of the plaintext.
TRIMMABLE_WHITESPACE = " \t\r\n\v\f"


def trim(text: str) -> str:
    """Strip surrounding layout whitespace, never payload bytes.

    ``str.strip()`` on its own would eat \x1c-\x1f, which are payload bytes in a
    peeled encoding rather than layout -- and eating them shifts every XOR key
    alignment that follows.

    >>> trim("  hello \\x1f ")
    'hello \\x1f'
    """
    return text.strip(TRIMMABLE_WHITESPACE)


def strip_space(text: str) -> str:
    """Remove all whitespace, preserving case and punctuation."""
    return _WS.sub("", text)


#: Accented and non-English Latin letters mapped onto their ASCII equivalents,
#: grouped by replacement.  Built per character: a table keyed by ``"àáâ"`` would
#: never match a single ``"à"``, which is exactly the bug this avoids.
_FOLD_GROUPS = {
    "a": "àáâãäåāăąǎǻª",
    "c": "çćĉċč",
    "d": "ðďđð",
    "e": "èéêëēĕėęě",
    "g": "ğĝġģǧ",
    "i": "ìíîïĩīĭįıǐ",
    "j": "ĵǰ",
    "k": "ķĸǩ",
    "l": "łļľŀŀ",
    "n": "ñńņňŉŋ",
    "o": "òóôõöøōŏőǒǫǭº",
    "r": "ŕŗř",
    "s": "śŝşšș",
    "t": "ţťŧț",
    "u": "ùúûüũūŭůűųǔǖǘǚǜ",
    "y": "ýÿŷ",
    "z": "źżž",
    "ae": "æǽ",
    "oe": "œ",
    "ss": "ßẞ",
    "th": "þ",
    "dh": "ð",
}
FOLD_TABLE: dict[str, str] = {}
for _replacement, _chars in _FOLD_GROUPS.items():
    for _ch in _chars:
        FOLD_TABLE.setdefault(_ch, _replacement)
del _replacement, _chars, _ch


def fold(text: str) -> str:
    """Best-effort transliteration of accented/Unicode letters to ASCII.

    Handles the common European cases so a French or German ciphertext can be
    attacked with the English model instead of dying on ``é``.  Case is
    preserved and unknown non-ASCII characters are dropped.

    >>> fold("Caf\u00e9 na\u00efve")
    'Cafe naive'
    >>> fold("Stra\u00dfe")
    'Strasse'
    """
    out = []
    for ch in text:
        mapped = FOLD_TABLE.get(ch.lower())
        if mapped:
            out.append(mapped.upper() if ch.isupper() else mapped)
        elif ord(ch) < 128:
            out.append(ch)
        # else: dropped -- a script we have no model for
    return "".join(out)


def normalise(text: str, *, fold_unicode: bool = True, keep: str = "letters") -> str:
    """One-call normalisation used by the engine before attacking.

    ``keep`` is ``letters`` (A-Z only), ``alnum``, ``printable`` or ``raw``.
    """
    if fold_unicode:
        text = fold(text)
    if keep == "letters":
        return letters_only(text)
    if keep == "alnum":
        return alnum_only(text)
    if keep == "printable":
        return printable_only(text)
    return text


def chunk(text: str, size: int = 5, sep: str = " ") -> str:
    """Group into fixed-size blocks -- classic ciphertext presentation."""
    if size <= 0:
        return text
    return sep.join(text[i : i + size] for i in range(0, len(text), size))


def frequencies(text: str, alphabet: str = A26) -> Counter:
    """Character frequency counter restricted to ``alphabet``."""
    keep = set(alphabet)
    return Counter(c for c in text.upper() if c in keep)


def relative_frequencies(text: str, alphabet: str = A26) -> dict[str, float]:
    """Character frequencies as proportions summing to ~1."""
    counts = frequencies(text, alphabet)
    total = sum(counts.values())
    if not total:
        return {c: 0.0 for c in alphabet}
    return {c: counts.get(c, 0) / total for c in alphabet}


def index_of_coincidence(text: str, alphabet: str = A26) -> float:
    """Friedman's index of coincidence.

    English prose sits near 0.066, random letters near 0.038, and a good
    transposition preserves the plaintext IC exactly.  That single number does a
    lot of the engine's cipher-identification work.
    """
    counts = frequencies(text, alphabet)
    n = sum(counts.values())
    if n < 2:
        return 0.0
    return sum(c * (c - 1) for c in counts.values()) / (n * (n - 1))


def entropy(data: str | bytes) -> float:
    """Shannon entropy in bits per symbol."""
    if isinstance(data, str):
        data = data.encode("utf-8", "replace")
    if not data:
        return 0.0
    total = len(data)
    import math

    return -sum((c / total) * math.log2(c / total) for c in Counter(data).values())


def ic_of_columns(text: str, key_len: int, alphabet: str = A26) -> float:
    """Mean IC of the ``key_len`` cosets a periodic cipher would produce."""
    cols = [text[i::key_len] for i in range(key_len)]
    ics = [index_of_coincidence(c, alphabet) for c in cols]
    ics = [v for v in ics if v]
    return sum(ics) / len(ics) if ics else 0.0


def best_key_length(text: str, max_len: int = 20, alphabet: str = A26) -> tuple[int, float]:
    """Kasiski-lite: the period whose cosets look most like English.

    Returns ``(key_length, mean_ic)``.  Periods that divide the true key length
    also score high, so callers should prefer the *smallest* strong candidate.
    """
    stream = letters_only(text, alphabet)
    if len(stream) < 2 * max_len:
        return 1, index_of_coincidence(stream, alphabet)
    scores = [(k, ic_of_columns(stream, k, alphabet)) for k in range(1, max_len + 1)]
    best = max(scores, key=lambda kv: kv[1])
    # Prefer a divisor of the best period with nearly the same IC (shorter key).
    for k, ic in scores:
        if k < best[0] and best[0] % k == 0 and ic >= best[1] * 0.97:
            return k, ic
    return best


def dedupe(seq):
    """Order-preserving deduplication."""
    seen = set()
    for item in seq:
        if item not in seen:
            seen.add(item)
            yield item


def keyed_alphabet(keyword: str, base: str = A26) -> str:
    """Build a keyed alphabet: keyword letters first, then the rest in order.

    >>> keyed_alphabet("LEMON")
    'LEMONABCDFGHIJKPQRSTUVWXYZ'
    """
    seen: list[str] = []
    for ch in letters_only(keyword, base):
        if ch not in seen:
            seen.append(ch)
    for ch in base:
        if ch not in seen:
            seen.append(ch)
    return "".join(seen)


def alphabet_mapping(source: str, target: str) -> dict[str, str]:
    """Positional mapping ``source[i] -> target[i]``."""
    if len(source) != len(target):
        raise ValueError("alphabets must be the same length")
    return dict(zip(source, target))


def apply_mapping(text: str, mapping: dict[str, str], *, invert: bool = False) -> str:
    if invert:
        mapping = {v: k for k, v in mapping.items()}
    table = str.maketrans(mapping)
    return text.translate(table)


def columnar(text: str, width: int) -> list[list[str]]:
    """Split into rows of ``width`` (last row may be short)."""
    return [list(text[i : i + width]) for i in range(0, len(text), width)]


def to_bytes(text: str) -> bytes:
    """Bytes for byte-oriented attacks; hex/utf-8 decoding lives in encodings."""
    return text.encode("utf-8", "surrogateescape")


def hamming_distance(a: bytes, b: bytes) -> int:
    return sum(bin(x ^ y).count("1") for x, y in zip(a, b))


def byte_ic(data: bytes) -> float:
    """Index of coincidence over the full 256-byte alphabet.

    >>> round(byte_ic(b"aaaa"), 3)
    1.0
    >>> round(byte_ic(bytes(range(64))), 4)
    0.0
    """
    n = len(data)
    if n < 2:
        return 0.0
    counts = Counter(data)
    return sum(c * (c - 1) for c in counts.values()) / (n * (n - 1))


def coset_byte_ic(data: bytes, size: int) -> float:
    """Mean byte IC of the ``size`` cosets -- the repeating-key-XOR period test.

    A coset taken at the true key length is the message XOR a single constant
    byte.  XOR with a constant is a bijection, so the English byte distribution
    keeps its skew and the IC stays near 0.07; at a wrong length the coset mixes
    several key bytes and the distribution flattens towards 1/256.  Working on
    bytes rather than letters is what makes this hold for binary payloads, where
    the plaintext has been shifted clean out of the printable range.
    """
    if size <= 0:
        return 0.0
    return sum(byte_ic(data[i::size]) for i in range(size)) / size


def divisors(n: int) -> tuple[int, ...]:
    """Proper divisors of ``n``, smallest first, excluding 1 and ``n`` itself.

    >>> divisors(12)
    (2, 3, 4, 6)
    """
    return tuple(d for d in range(2, n) if n % d == 0)


def normalised_hamming(data: bytes, size: int) -> float:
    """Mean normalised Hamming distance between blocks -- repeating-key XOR tell."""
    blocks = [data[i : i + size] for i in range(0, len(data) - size + 1, size)]
    if len(blocks) < 2:
        return float("inf")
    total, pairs = 0.0, 0
    for i in range(len(blocks)):
        for j in range(i + 1, min(len(blocks), i + 8)):
            total += hamming_distance(blocks[i], blocks[j]) / size
            pairs += 1
    return total / pairs if pairs else float("inf")


def best_block_size(data: bytes, max_size: int = 40) -> tuple[int, float]:
    """Block size with the lowest normalised Hamming distance.

    The classic repeating-key-XOR tell.  Note that the winner may be a *multiple*
    of the true key length: blocks taken at 12 bytes over a 3-byte key are
    byte-identical, so they score at least as well as blocks taken at 3.  Treat
    the result as "a period", not as "the period" -- the XOR attack ranks
    several lengths and lets the recovered plaintext choose.
    """
    if len(data) < 2 * max_size:
        max_size = max(2, len(data) // 2)
    scores = [(size, normalised_hamming(data, size)) for size in range(2, max_size + 1)]
    scores = [(s, d) for s, d in scores if d != float("inf")]
    if not scores:
        return 1, float("inf")
    return min(scores, key=lambda kv: kv[1])


def map_letters(
    text: str,
    transform: "Callable[[int, int], int]",
    *,
    alphabet: str = A26,
) -> str:
    """Apply ``transform(position, index)`` to every letter and keep the rest.

    ``position`` counts *letters only*, so a repeating key advances on letters and
    not on punctuation; ``index`` is the letter's position in ``alphabet``,
    ignoring case; the result is emitted in the case of the original character.
    Everything that is not a letter in ``alphabet`` is copied through untouched,
    which is what makes ``encrypt("Hello, world!")`` give ``"Khoor, zruog!"``
    rather than ``"KHOORZRUOG"``.

    >>> map_letters("Hello, world!", lambda i, x: (x + 3) % 26)
    'Khoor, zruog!'
    >>> map_letters("Ab C", lambda i, x: x + i)
    'Ac E'
    """
    upper = alphabet.upper()
    size = len(upper)
    out: list[str] = []
    position = 0
    for ch in text:
        idx = upper.find(ch.upper()) if ch.isascii() else -1
        if idx < 0:
            out.append(ch)
            continue
        letter = upper[transform(position, idx) % size]
        out.append(letter.lower() if ch.islower() else letter)
        position += 1
    return "".join(out)


def is_word_shaped(text: str) -> bool:
    """True when whitespace separates short all-alphabetic words: prose, not a blob.

    Encoded payloads arrive either as one unbroken run or wrapped at a fixed
    column (64 or 76 for MIME base64, byte pairs for hex), so a run of short
    alphabetic words is a *message*, whatever alphabet it happens to fit.
    ``"Wkh txlfn eurzq ira"`` matches the base64 alphabet perfectly and is still
    a Caesar ciphertext -- the layout is what tells the two apart.

    >>> is_word_shaped("Wkh txlfn eurzq ira")
    True
    >>> is_word_shaped("VGhpcyBpcyBhIGJhc2U2NCBzdHJpbmc=")
    False
    >>> is_word_shaped("48 65 6c 6c 6f")
    False
    """
    words = text.split()
    if len(words) < 3 or not all(w.isalpha() for w in words):
        return False
    average = sum(len(w) for w in words) / len(words)
    return 0 < average <= 12


def restore_shape(letters: str, template: str) -> str | None:
    """Re-apply the original spacing, punctuation and case to solved letters.

    Position-preserving ciphers (Caesar, substitution, Vigenere, Playfair) keep
    every non-letter character and the case pattern of the message, so the
    readable layout of the original can be laid back over the recovered letters.
    Returns ``None`` when the shapes are incompatible -- which is the signal that
    a transposition was involved and word breaks must be re-derived instead.

    >>> restore_shape("ATTACKATDAWN", "Xxxxxx xx xxxx")
    'Attack at dawn'
    """
    out: list[str] = []
    it = iter(letters.upper())
    used = 0
    for ch in template:
        if ch.isalpha() and ch.isascii():
            try:
                letter = next(it)
            except StopIteration:
                return None
            used += 1
            out.append(letter.lower() if ch.islower() else letter)
        else:
            out.append(ch)
    if used != len(letters):
        return None
    return "".join(out)


def respaced(letters: str, words) -> str:
    """Join a segmentation back into readable prose."""
    return " ".join(w for w in words if w)
