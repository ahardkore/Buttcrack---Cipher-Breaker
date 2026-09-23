"""buttcrack -- an automatic cipher breaker.

Point it at a ciphertext and it works out what was used, recovers the key and
returns the plaintext -- including layered puzzles, where a classical cipher
sits inside an encoding (``base64`` -> ``caesar`` -> English).

    >>> from buttcrack import solve
    >>> r = solve("Uryyb, jbeyq! Guvf vf n grfg bs gur nhgbzngvp oernxre.")
    >>> r.cipher, round(r.confidence, 2)   # a shift of 13 gets its own name
    ('rot13', 1.0)
    >>> r.formatted[:19]                   # case and punctuation come back too
    'Hello, world! This '

Everything runs on the Python standard library; no network access, no external
services, no dependencies. See :mod:`buttcrack.engine` for the search,
:mod:`buttcrack.detect` for identification, and :mod:`buttcrack.ciphers` for
the algorithms themselves.
"""

from __future__ import annotations

from typing import Any

from .ciphers import (
    ALL_CIPHERS,
    BY_NAME,
    CIPHERS,
    Cipher,
    CipherInfo,
    by_family,
    get,
    try_get,
)
from .detect import TextStats, characterise, identify
from .engine import Solver, solve
from .results import AttackLog, Candidate, CrackReport, Hypothesis
from .text import best_key_length, frequencies, normalise, restore_shape


def encrypt(plaintext: str, cipher: str | Cipher, key: Any = None) -> str:
    """Encrypt ``plaintext`` with a named cipher.

    ``key=None`` uses the cipher's own example key, which is what you want for a
    demonstration and wrong for anything else -- pass a key.

        >>> encrypt("Meet me at noon.", "vigenere", "LEMON")
        'Xiqh zp ef bbzr.'
        >>> encrypt("Attack at dawn", "caesar", 3)
        'Dwwdfn dw gdzq'
    """
    target = cipher if isinstance(cipher, Cipher) else get(str(cipher))
    return target.encrypt(plaintext, target.info.example_key if key is None else key)


def decrypt(ciphertext: str, cipher: str | Cipher, key: Any = None) -> str:
    """Decrypt ``ciphertext`` with a named cipher and key.

        >>> decrypt("Xiqh zp ef bbzr.", "vigenere", "LEMON")
        'Meet me at noon.'
    """
    target = cipher if isinstance(cipher, Cipher) else get(str(cipher))
    return target.decrypt(ciphertext, target.info.example_key if key is None else key)


__all__ = [
    "ALL_CIPHERS",
    "AttackLog",
    "BY_NAME",
    "CIPHERS",
    "Candidate",
    "Cipher",
    "CipherInfo",
    "CrackReport",
    "Hypothesis",
    "Solver",
    "TextStats",
    "best_key_length",
    "by_family",
    "characterise",
    "decrypt",
    "encrypt",
    "frequencies",
    "get",
    "identify",
    "normalise",
    "restore_shape",
    "solve",
    "try_get",
]

__version__ = "1.0.0"
