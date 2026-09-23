"""The cipher registry.

Every cipher module registers itself here on import, and the engine, the CLI and
the web API all talk to the registry rather than to concrete classes.  Adding a
cipher is therefore a two-step change: write the class, add it to
:data:`ALL_CIPHERS`.
"""

from __future__ import annotations

from typing import Iterator

from .base import (
    BRUTAL,
    CHEAP,
    EXPENSIVE,
    MODERATE,
    Cipher,
    CipherInfo,
    CrackContext,
    Family,
    LayerCipher,
)
from .codes import A1Z26, Bacon, BaconCase, Morse, Polybius
from .encodings import (
    Base16,
    Base32,
    Base58,
    Base64,
    Base85,
    BinaryASCII,
    DecimalASCII,
    PercentEncoding,
)
from .polygraphic import Bifid, Playfair
from .shift import ROT13, ROT47, Affine, Atbash, Caesar, Reverse
from .substitution import KeywordSubstitution, Substitution
from .transposition import ColumnarTransposition, RailFence, RouteTransposition, SkipTransposition
from .xor import RepeatingKeyXOR, SingleByteXOR
from .polyalphabetic import (
    Autokey,
    Beaufort,
    Gronsfeld,
    Trithemius,
    VariantBeaufort,
    Vigenere,
)

#: Every cipher Buttcrack knows, in the order they are displayed.
ALL_CIPHERS: list[Cipher] = [
    # shift family -- cheapest first
    Caesar(),
    ROT13(),
    Atbash(),
    Affine(),
    ROT47(),
    Reverse(),
    # polyalphabetic
    Vigenere(),
    Beaufort(),
    VariantBeaufort(),
    Gronsfeld(),
    Trithemius(),
    Autokey(),
    # substitution
    Substitution(),
    KeywordSubstitution(),
    # transposition
    ColumnarTransposition(),
    RailFence(),
    SkipTransposition(),
    RouteTransposition(),
    # polygraphic
    Playfair(),
    Bifid(),
    # byte level
    SingleByteXOR(),
    RepeatingKeyXOR(),
    # codes
    Morse(),
    Bacon(),
    BaconCase(),
    A1Z26(),
    Polybius(),
    # encodings
    Base64(),
    Base32(),
    Base16(),
    Base58(),
    Base85(),
    PercentEncoding(),
    BinaryASCII(),
    DecimalASCII(),
]

#: name/alias -> cipher
BY_NAME: dict[str, Cipher] = {}
for _cipher in ALL_CIPHERS:
    BY_NAME[_cipher.info.name] = _cipher
    for _alias in _cipher.info.aliases:
        BY_NAME.setdefault(_alias.lower(), _cipher)


#: Convenience alias -- ``CIPHERS`` reads better in scripts.
CIPHERS = ALL_CIPHERS


def all_ciphers() -> list[Cipher]:
    return list(ALL_CIPHERS)


def get(name: str) -> Cipher:
    """Look up a cipher by name or alias (case-insensitive)."""
    key = str(name).strip().lower().replace(" ", "_").replace("-", "_")
    if key not in BY_NAME:
        raise KeyError(f"unknown cipher {name!r}; try `buttcrack ciphers` for the list")
    return BY_NAME[key]


def try_get(name: str) -> Cipher | None:
    return BY_NAME.get(str(name).strip().lower())


def by_family() -> dict[str, list[Cipher]]:
    out: dict[str, list[Cipher]] = {}
    for cipher in ALL_CIPHERS:
        out.setdefault(cipher.info.family.value, []).append(cipher)
    return out


def layer_ciphers() -> list[LayerCipher]:
    """Encoding layers the recursive peeler may strip."""
    return [c for c in ALL_CIPHERS if isinstance(c, LayerCipher) and c.info.layer]


def attack_ciphers(families: tuple[Family, ...] | None = None) -> list[Cipher]:
    """Ciphers worth *attacking* (as opposed to peeling), ordered by cost."""
    out = [c for c in ALL_CIPHERS if not isinstance(c, LayerCipher)]
    # Codes are decoders rather than attacks, but they can be the answer.
    out += [c for c in ALL_CIPHERS if isinstance(c, LayerCipher) and c.info.family in (Family.CODE,)]
    if families:
        out = [c for c in out if c.info.family in families]
    seen: dict[str, Cipher] = {}
    for cipher in out:
        seen.setdefault(cipher.info.name, cipher)
    return sorted(seen.values(), key=lambda c: (c.info.cost, c.info.name))


def cost_class(cipher: Cipher) -> float:
    return cipher.info.cost


__all__ = [
    "ALL_CIPHERS",
    "CIPHERS",
    "BY_NAME",
    "BRUTAL",
    "CHEAP",
    "EXPENSIVE",
    "MODERATE",
    "Cipher",
    "CipherInfo",
    "CrackContext",
    "Family",
    "LayerCipher",
    "all_ciphers",
    "attack_ciphers",
    "by_family",
    "get",
    "layer_ciphers",
    "try_get",
]
