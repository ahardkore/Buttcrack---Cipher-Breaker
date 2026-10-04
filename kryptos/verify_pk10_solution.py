#!/usr/bin/env python3
"""Verify the recovered Paradigm Kryptos PK10 construction.

PK10 is not a three-clock / 12x42 cipher.  The recovered construction is the
full cumulative pipeline used by the public reference implementation:

    Q3(PROVENANCE)
    T(MARGINS)
    Q3(ORDINATE) Q3(PENTIMENTO)
    T(UNDERLAY) Q3(OCHRE) Q3(VERDIGRIS)
    T(TWOYEARS) Q3(PK4 plaintext)
    T(HANDIWORK) T(SMITHWORK) Q3(PORTAL)
    Q3(ANNEAL) H3(ALCHEMIST)
    Q3(METE) Q3(METER) Q3(METIER) Q3(MASTERY)
    Q3(CLEPSYDRA) Spiral(12) T(BEAMWORK)

The alphabet is KRYPTOSABCDEFGHIJLMNQUVWXZ.  Q3 is additive in the keyed
alphabet's index space.  T fills a rectangular grid row-wise, permutes columns
by the alphabetical rank of its keyword, and reads columns top-to-bottom.
H3 uses the nine letters of ALCHEMIST as a row-major matrix over Z/26Z.

This verifier is intentionally dependency-free and checks both directions:
- encode the recovered 504-letter plaintext and compare every ciphertext letter;
- decode the official ciphertext and compare the recovered plaintext exactly.

The recovered text and pipeline were published in TTFH/KRYPTOS, commit
496976ebe008f9a5eaef8c52bb8ad06c3a4917f5, src/ctf/PK10.h.  The exact
round-trip against the canonical ciphertext is the local acceptance criterion.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent
KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
INDEX = {char: i for i, char in enumerate(KRYPTOS)}

PK10_PLAINTEXT = (
    "IHAVENOTREADTHESTRAND"
    "THENEEDLEWASASFINEASPROMISED"
    "BUTMYHANDWASNOTFITTOWIELDIT"
    "ANDTHEKNOTREFUSEDTOYIELD"
    "PELLEGRINANDTHEWHITESMITHTRIEDTOTEACHME"
    "BUTWHENTHETESTCAMEIFAILEDTHEMBOTH"
    "HADISTAYEDWITHTHEWHITESMITHANDLEARNEDTHEDISCIPLINEHETAUGHT"
    "THOSEYEARS"
    "WOULDHAVESHAPEDMYHANDSINTOINSTRUMENTSWORTHYOFTHENEEDLEANDTHEKNOT"
    "ANDATLASTGIVENMETHELOCATIONOFTHEARCHIVE"
    "PELLEGRINHIDITFORONLYSUCHASUCCESSOR"
    "THROUGHPATIENCEDISCIPLINEANDTRUECRAFT"
    "TOYOUWHOHAVEUNRAVELEDMYMESSAGES"
    "YOURHANDISTHENEEDLEIHAVEFINALLYFORGED"
    "ANDILEAVETHEKNOTTOYOU"
)

# This is the PK4 plaintext used as the 224-character running Q3 key.
PK4_PLAINTEXT = (
    "TWOYEARSINTHENEEDLESTRAILLEDMETOACRAFTSMANNAMEDTHEWHITESMITH"
    "ONTHEROADTOHISALPINEWORKSHOPIREREADHISPERFUNCTORYLETTERS"
    "HEMETMEATTHEGATESANDLEDMETOASTONEBARNSTACKEDWITHWINTERFODDER"
    "ONEOFHISNEEDLESISHIDDENINTHEBARNIHAVEBEGUNTOWORK"
)

# The canonical ciphertext is loaded from pk_all_ciphertexts.json rather than
# duplicated here, so the verifier cannot silently drift from the repository's
# official corpus.


def _deduplicate(text: str) -> str:
    return "".join(dict.fromkeys(text))


def q3(text: str, key: str, *, encode: bool) -> str:
    """Quagmire III over the KRYPTOS keyed alphabet."""
    shifts = [INDEX[char] for char in key]
    direction = 1 if encode else -1
    return "".join(
        KRYPTOS[(INDEX[char] + direction * shifts[pos % len(shifts)]) % 26]
        for pos, char in enumerate(text)
    )


def _column_ranks(keyword: str) -> list[int]:
    # The reference implementation rejects duplicate-key keywords.  All PK10
    # keywords are distinct, but keeping the check makes the convention explicit.
    if len(set(keyword)) != len(keyword):
        raise ValueError(f"column keyword has duplicate letters: {keyword}")
    return [sum(keyword[other] < keyword[index] for other in range(len(keyword)))
            for index in range(len(keyword))]


def columnar(text: str, keyword: str, *, encode: bool) -> str:
    """Encode/decode the reference complete columnar transposition."""
    width = len(keyword)
    if len(text) % width:
        raise ValueError(f"{len(text)} is not divisible by column width {width}")
    height = len(text) // width
    ranks = _column_ranks(keyword)

    if encode:
        rows = [list(text[row * width:(row + 1) * width]) for row in range(height)]
        swapped = [[""] * width for _ in range(height)]
        for row in range(height):
            for col in range(width):
                swapped[row][ranks[col]] = rows[row][col]
        return "".join(swapped[row][col] for col in range(width) for row in range(height))

    swapped = [[""] * width for _ in range(height)]
    for col in range(width):
        for row in range(height):
            swapped[row][col] = text[col * height + row]
    rows = [[swapped[row][ranks[col]] for col in range(width)] for row in range(height)]
    return "".join(char for row in rows for char in row)


def _spiral_order(rows: int, cols: int) -> list[tuple[int, int]]:
    # Down, left, up, right; start at the top-right cell.
    moves = ((1, 0), (0, -1), (-1, 0), (0, 1))
    seen: set[tuple[int, int]] = set()
    result: list[tuple[int, int]] = []
    row, col, direction = 0, cols - 1, 0
    for _ in range(rows * cols):
        result.append((row, col))
        seen.add((row, col))
        next_row = row + moves[direction][0]
        next_col = col + moves[direction][1]
        if not (0 <= next_row < rows and 0 <= next_col < cols) or (next_row, next_col) in seen:
            direction = (direction + 1) % 4
            next_row = row + moves[direction][0]
            next_col = col + moves[direction][1]
        row, col = next_row, next_col
    return result


def spiral(text: str, width: int, *, encode: bool) -> str:
    if len(text) % width:
        raise ValueError(f"{len(text)} is not divisible by spiral width {width}")
    height = len(text) // width
    order = _spiral_order(height, width)
    if encode:
        return "".join(text[row * width + col] for row, col in order)
    rows = [""] * len(text)
    for index, (row, col) in enumerate(order):
        rows[row * width + col] = text[index]
    return "".join(rows)


def _determinant(matrix: list[list[int]]) -> int:
    a, b, c = matrix[0]
    d, e, f = matrix[1]
    g, h, i = matrix[2]
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def _inverse_mod_26(matrix: list[list[int]]) -> list[list[int]]:
    a, b, c = matrix[0]
    d, e, f = matrix[1]
    g, h, i = matrix[2]
    adjugate = [
        [e * i - f * h, c * h - b * i, b * f - c * e],
        [f * g - d * i, a * i - c * g, c * d - a * f],
        [d * h - e * g, b * g - a * h, a * e - b * d],
    ]
    determinant = _determinant(matrix) % 26
    inverse_determinant = next(
        (candidate for candidate in range(26) if determinant * candidate % 26 == 1),
        None,
    )
    if inverse_determinant is None:
        raise ValueError(f"Hill matrix is not invertible modulo 26 (det={determinant})")
    return [
        [(inverse_determinant * value) % 26 for value in row]
        for row in adjugate
    ]


def hill3(text: str, keyword: str, *, encode: bool) -> str:
    if len(keyword) != 9 or len(text) % 3:
        raise ValueError("PK10 H3 requires a nine-letter key and 3-letter blocks")
    values = [INDEX[char] for char in keyword]
    matrix = [values[row * 3:(row + 1) * 3] for row in range(3)]
    if not encode:
        matrix = _inverse_mod_26(matrix)

    output: list[str] = []
    for start in range(0, len(text), 3):
        vector = [INDEX[char] for char in text[start:start + 3]]
        output.extend(
            KRYPTOS[sum(matrix[row][col] * vector[col] for col in range(3)) % 26]
            for row in range(3)
        )
    return "".join(output)


# Callable layer descriptors keep the order visible in the verifier and make
# the reverse decode mechanically identical to the forward encode.
Layer = tuple[str, str | int | None, Callable[[str, str | int | None, bool], str]]


def _q_layer(key: str) -> Layer:
    return (f"Q3({key})", key, lambda text, arg, encode: q3(text, str(arg), encode=encode))


def _column_layer(key: str) -> Layer:
    return (f"T({key})", key, lambda text, arg, encode: columnar(text, str(arg), encode=encode))


def _hill_layer(key: str) -> Layer:
    return (f"H3({key})", key, lambda text, arg, encode: hill3(text, str(arg), encode=encode))


def _spiral_layer(width: int) -> Layer:
    return (f"Spiral({width})", width, lambda text, arg, encode: spiral(text, int(arg), encode=encode))


def layers() -> list[Layer]:
    return [
        _q_layer("PROVENANCE"),
        _column_layer("MARGINS"),
        _q_layer("ORDINATE"),
        _q_layer("PENTIMENTO"),
        _column_layer("UNDERLAY"),
        _q_layer("OCHRE"),
        _q_layer("VERDIGRIS"),
        _column_layer("TWOYEARS"),
        _q_layer(PK4_PLAINTEXT),
        _column_layer("HANDIWORK"),
        _column_layer("SMITHWORK"),
        _q_layer("PORTAL"),
        _q_layer("ANNEAL"),
        _hill_layer("ALCHEMIST"),
        _q_layer("METE"),
        _q_layer("METER"),
        _q_layer("METIER"),
        _q_layer("MASTERY"),
        _q_layer("CLEPSYDRA"),
        _spiral_layer(12),
        _column_layer("BEAMWORK"),
    ]


def encode(text: str) -> str:
    for _, arg, function in layers():
        text = function(text, arg, True)
    return text


def decode(text: str) -> str:
    for _, arg, function in reversed(layers()):
        text = function(text, arg, False)
    return text


def main() -> None:
    ciphertexts = json.loads((ROOT / "pk_all_ciphertexts.json").read_text(encoding="utf-8"))
    ciphertext = ciphertexts["PK10"]
    encoded = encode(PK10_PLAINTEXT)
    decoded = decode(ciphertext)

    checks = {
        "plaintext length": len(PK10_PLAINTEXT) == 504,
        "PK4 running-key length": len(PK4_PLAINTEXT) == 224,
        "ciphertext length": len(ciphertext) == 504,
        "encode exact match": encoded == ciphertext,
        "decode exact match": decoded == PK10_PLAINTEXT,
        "plaintext SHA-256": hashlib.sha256(PK10_PLAINTEXT.encode("ascii")).hexdigest()
        == "a2db145f258ec21fbeab7afb4031e624d3184b93a3eb834d54026ba9b792e1d9",
    }
    print("PK10 recovered-construction verification")
    print("==========================================")
    for name, passed in checks.items():
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
    print(f"Layers: {len(layers())}")
    print(f"Plaintext: {PK10_PLAINTEXT}")
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
