#!/usr/bin/env python3
"""Layered-solver benchmark: does the search still come apart at depth?

Unit tests say *whether* a case works; this says how long it took and what
chain came back, which is what you need when tuning the scheduler.  Every knob
in the engine -- how much of the clock a child node gets, how many transposition
readings are probed, how much evidence a deep peel needs -- trades one case
against another, and the only way to tune one honestly is to watch all of them
at once.

    python3 scripts/bench_layers.py

Cases are ordered from "must never break" (a bare Caesar) to the deep stacks
the layering work is for.  A run takes about two minutes.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from buttcrack import solve  # noqa: E402
from buttcrack.ciphers import get  # noqa: E402

SENTENCE = (
    "The archive contains the original manuscripts, three of which were lost during the fire of "
    "eighteen ninety two, and the catalogue that described them was destroyed as well."
)
LONG = SENTENCE + (
    " Every secret society in the city maintains at least one archive of forbidden documents, "
    "and the committee has decided to postpone the railway conference."
)
SHORT = "Meet the courier beneath the clock tower at dawn"


def enc(name: str, text: str, *key) -> str:
    """Encrypt with a cipher, or encode with a layer."""
    cipher = get(name)
    if key:
        return cipher.encrypt(text, *key)
    return cipher.encode(text) if hasattr(cipher, "encode") else cipher.encrypt(text)


#: (label, ciphertext, expected plaintext, budget in seconds)
CASES = [
    ("caesar", enc("caesar", SENTENCE, 7), SENTENCE, 20),
    ("vigenere", enc("vigenere", SENTENCE, "LEMON"), SENTENCE, 20),
    ("porta", enc("porta", SENTENCE, "LANTERN"), SENTENCE, 20),
    ("substitution", enc("substitution", LONG, "QWERTYUIOPASDFGHJKLZXCVBNM"), LONG, 25),
    ("columnar", enc("columnar", SENTENCE, "ZEBRA"), SENTENCE, 20),
    ("myszkowski", enc("myszkowski", SENTENCE, "TOMATO"), SENTENCE, 20),
    ("amsco", enc("amsco", SENTENCE, "ZEBRA"), SENTENCE, 20),
    ("hill", enc("hill", SENTENCE, "HILL"), SENTENCE, 20),
    ("rot47", enc("rot47", SENTENCE, 47), SENTENCE, 20),
    ("morse", enc("morse", SENTENCE), SENTENCE, 15),
    ("nato", enc("nato", SENTENCE), SENTENCE, 15),
    ("tap_code", enc("tap_code", SENTENCE), SENTENCE, 15),
    ("baudot", enc("baudot", SENTENCE), SENTENCE, 15),
    # A keyed Polybius is a peel followed by a substitution search underneath.
    ("keyed polybius", enc("polybius", SENTENCE, "MONARCHY"), SENTENCE, 15),
    ("base64(caesar)", enc("base64", enc("caesar", SENTENCE, 5)), SENTENCE, 20),
    ("base32(base64(caesar))", enc("base32", enc("base64", enc("caesar", SENTENCE, 9))), SENTENCE, 20),
    # Cipher-on-cipher: the reading cannot be ranked, only tried.
    ("rail_fence(caesar)", enc("rail_fence", enc("caesar", SENTENCE, 5), 4), SENTENCE, 25),
    ("reverse(vigenere)", enc("reverse", enc("vigenere", SENTENCE, "LEMON")), SENTENCE, 25),
    ("skip(vigenere)", enc("skip", enc("vigenere", SENTENCE, "LEMON"), 5), SENTENCE, 25),
    (
        "5 layers",
        enc("base16", enc("base64", enc("morse", enc("reverse", enc("caesar", SHORT, 7))))),
        SHORT,
        25,
    ),
    (
        "6 layers",
        enc("base32", enc("base16", enc("base64", enc("morse", enc("reverse", enc("caesar", SHORT, 11)))))),
        SHORT,
        25,
    ),
    # Stacks of *ciphers* rather than encodings.  These are the cases the chain
    # search exists for: transpositions and substitutions commute, so a stack
    # of them is one permutation plus one substitution however deep it goes.
    (
        "3 ciphers deep",
        enc("reverse", enc("rail_fence", enc("caesar", SENTENCE, 5), 4)),
        SENTENCE,
        25,
    ),
    (
        "4 ciphers deep",
        enc("skip", enc("reverse", enc("rail_fence", enc("atbash", SENTENCE), 3)), 4),
        SENTENCE,
        25,
    ),
    (
        "5 ciphers deep",
        enc("rail_fence", enc("skip", enc("reverse", enc("rail_fence", enc("caesar", SENTENCE, 7), 3)), 5), 4),
        SENTENCE,
        25,
    ),
    (
        "6 ciphers deep",
        enc("reverse", enc("rail_fence", enc("skip", enc("reverse", enc("rail_fence", enc("rot13", SENTENCE), 3)), 5), 4)),
        SENTENCE,
        30,
    ),
    # A mixed stack: encodings outside, a cipher chain inside.
    (
        "encodings + cipher chain",
        enc("base64", enc("morse", enc("reverse", enc("rail_fence", enc("caesar", SENTENCE, 9), 3)))),
        SENTENCE,
        30,
    ),
]


def squash(text: str) -> str:
    """Letters only, I/J folded: the comparison the lossy grids deserve."""
    return "".join(c for c in text.upper() if c.isalpha()).replace("J", "I")


def main() -> int:
    passed = 0
    total = 0.0
    for label, ciphertext, plaintext, budget in CASES:
        started = time.time()
        report = solve(ciphertext, budget=budget, workers=2)
        elapsed = time.time() - started
        total += elapsed
        got, want = squash(report.plaintext)[:60], squash(plaintext)[:60]
        ok = got == want
        passed += ok
        print(
            f"{'PASS' if ok else 'FAIL'} {label:24} {elapsed:5.1f}s "
            f"conf={report.confidence:.2f} {report.path}"
        )
        if not ok:
            print(f"      got  {got}")
    print(f"\n{passed}/{len(CASES)} passed in {total:.0f}s")
    return 0 if passed == len(CASES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
