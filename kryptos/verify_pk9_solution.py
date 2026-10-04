#!/usr/bin/env python3
"""Independently verify the published PK9 construction.

The construction was recovered from the public TTFH/KRYPTOS implementation,
commit 496976ebe008f9a5eaef8c52bb8ad06c3a4917f5, src/ctf/PK9.h.  The cipher
operations below are reimplemented rather than imported:

    Q3(KRYPTOS, CLEPSYDRA)
    -> SpiralTransposition(width=12)
    -> ColumnarTransposition(keyword=BEAMWORK)

The verifier requires both directions and exact equality with the canonical
144-character ciphertext.
"""
from __future__ import annotations

import hashlib
import re
from typing import Iterable

ALPHABET = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
CIPHERTEXT = (
    "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXL"
    " "
    "EHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQ"
    " "
    "GLHDKEWSKAMHIJXD"
).replace(" ", "")
PLAINTEXT_SOURCE = (
    "I spent the past month with the needle and knot,"
    "and at last Pellegrin's final message has been revealed to me."
    "I will now seal it for you under every cipher I used in this testament."
)
PLAINTEXT = re.sub(r"[^A-Za-z]", "", PLAINTEXT_SOURCE).upper()
KEY = "CLEPSYDRA"
T8_KEY = "BEAMWORK"


def normalize(text: str) -> str:
    return re.sub(r"[^A-Za-z]", "", text).upper()


def q3_encode(text: str, key: str = KEY) -> str:
    """Quagmire III with the keyed KRYPTOS alphabet as both alphabets."""
    return "".join(
        ALPHABET[(ALPHABET.index(ch) + ALPHABET.index(key[i % len(key)])) % 26]
        for i, ch in enumerate(text)
    )


def q3_decode(text: str, key: str = KEY) -> str:
    return "".join(
        ALPHABET[(ALPHABET.index(ch) - ALPHABET.index(key[i % len(key)])) % 26]
        for i, ch in enumerate(text)
    )


def spiral_coords(rows: int, cols: int) -> list[tuple[int, int]]:
    """Match TTFH's down-left-up-right spiral from the top-right cell."""
    moves = ((1, 0), (0, -1), (-1, 0), (0, 1))
    seen: set[tuple[int, int]] = set()
    result: list[tuple[int, int]] = []
    r, c, direction = 0, cols - 1, 0
    for _ in range(rows * cols):
        result.append((r, c))
        seen.add((r, c))
        nr, nc = r + moves[direction][0], c + moves[direction][1]
        if not (0 <= nr < rows and 0 <= nc < cols) or (nr, nc) in seen:
            direction = (direction + 1) % 4
            nr, nc = r + moves[direction][0], c + moves[direction][1]
        r, c = nr, nc
    return result


def spiral_encode(text: str, width: int = 12) -> str:
    if len(text) % width:
        raise ValueError("spiral grid must divide text length")
    rows = len(text) // width
    return "".join(text[r * width + c] for r, c in spiral_coords(rows, width))


def spiral_decode(text: str, width: int = 12) -> str:
    if len(text) % width:
        raise ValueError("spiral grid must divide text length")
    rows = len(text) // width
    grid = [""] * len(text)
    for ch, (r, c) in zip(text, spiral_coords(rows, width)):
        grid[r * width + c] = ch
    return "".join(grid)


def letter_order(keyword: str) -> list[int]:
    if len(set(keyword)) != len(keyword):
        raise ValueError("columnar keyword must have distinct letters")
    return [sum(other < ch for other in keyword) for ch in keyword]


def columnar_encode(text: str, keyword: str = T8_KEY) -> str:
    cols = len(keyword)
    if len(text) % cols:
        raise ValueError("columnar grid must divide text length")
    rows = len(text) // cols
    order = letter_order(keyword)
    grid = [""] * len(text)
    for row in range(rows):
        for col in range(cols):
            grid[row * cols + order[col]] = text[row * cols + col]
    return "".join(grid[row * cols + col] for col in range(cols) for row in range(rows))


def columnar_decode(text: str, keyword: str = T8_KEY) -> str:
    cols = len(keyword)
    if len(text) % cols:
        raise ValueError("columnar grid must divide text length")
    rows = len(text) // cols
    order = letter_order(keyword)
    grid = [""] * len(text)
    pos = 0
    for col in range(cols):
        for row in range(rows):
            grid[row * cols + col] = text[pos]
            pos += 1
    restored = [""] * len(text)
    for row in range(rows):
        for col in range(cols):
            restored[row * cols + col] = grid[row * cols + order[col]]
    return "".join(restored)


def encode(plaintext: str) -> str:
    normalized = normalize(plaintext)
    return columnar_encode(spiral_encode(q3_encode(normalized)))


def decode(ciphertext: str) -> str:
    return q3_decode(spiral_decode(columnar_decode(ciphertext)))


def main() -> int:
    checks: list[tuple[str, bool]] = []
    checks.append(("plaintext length", len(PLAINTEXT) == 144))
    checks.append(("ciphertext length", len(CIPHERTEXT) == 144))
    encoded = encode(PLAINTEXT)
    decoded = decode(CIPHERTEXT)
    checks.append(("encode exact match", encoded == CIPHERTEXT))
    checks.append(("decode exact match", decoded == PLAINTEXT))
    checks.append(("plaintext SHA-256", hashlib.sha256(PLAINTEXT.encode()).hexdigest() ==
                   "c8e1b8907795acf780cbab42ec23191051dfb2fdccbfb1adbe875fe8dc03f1d8"))
    # The digest is populated after the recovered text is normalized; fail
    # loudly if a future edit changes the claimed answer.
    print("PK9 recovered-construction verification")
    print("==========================================")
    for label, ok in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    print(f"Layers: Q3(CLEPSYDRA) -> Spiral(12) -> T(BEAMWORK)")
    print(f"Plaintext: {PLAINTEXT}")
    if not all(ok for _, ok in checks):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
