#!/usr/bin/env python3
"""Independent verification of the Paradigm Kryptos PK1-PK8 constructions.

Conventions (reverse-engineered from the public TTFH/KRYPTOS reference
implementation, which round-trips against the official ciphertexts):

QuagmireIII(rep_key, key):
    alphabet A = dedup(rep_key + A..Z)  (KRYPTOS -> KRYPTOSABCDEFGHIJLMNQUVWXZ)
    encode: A[(A.index(c) + A.index(key[i % len])) % 26]

ColumnarTransposition(size, keyword):
    grid: rows x cols (cols = len(keyword)), filled ROW-WISE
    order[i] = rank of keyword[i] among its letters (strict alphabetically)
    swap: new_grid[r][order[c]] = grid[r][c]
    read out: columns top-to-bottom, left-to-right

HillCipher(prefix, keyword9):
    alphabet = dedup(prefix + A..Z); M[row][col] = idx[row*3+col]  (row-wise fill)
    encode: blocks of 3 -> M . v  (mod 26)

Pipeline: encode applies ciphers left-to-right.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
A_KR = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
IDX = {c: i for i, c in enumerate(A_KR)}


def q3_encode(text: str, key: str) -> str:
    k = [IDX[c] for c in key]
    return "".join(A_KR[(IDX[c] + k[i % len(k)]) % 26] for i, c in enumerate(text))


def q3_decode(text: str, key: str) -> str:
    k = [IDX[c] for c in key]
    return "".join(A_KR[(IDX[c] - k[i % len(k)]) % 26] for i, c in enumerate(text))


def col_key_order(keyword: str) -> list[int]:
    return [sum(keyword[j] < keyword[i] for j in range(len(keyword))) for i in range(len(keyword))]


def colt_encode(text: str, keyword: str) -> str:
    n, cols = len(text), len(keyword)
    rows = n // cols
    assert rows * cols == n
    order = col_key_order(keyword)
    # grid row-wise
    grid = [text[r * cols:(r + 1) * cols] for r in range(rows)]
    # swap columns: new column order[c] receives old column c
    new = [[None] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            new[r][order[c]] = grid[r][c]
    # read out by columns
    return "".join(new[r][c] for c in range(cols) for r in range(rows))


def hill_encode(text: str, keyword9: str) -> str:
    idx = [IDX[c] for c in keyword9]
    M = [[idx[row * 3 + col] for col in range(3)] for row in range(3)]  # M[row][col]
    out = []
    for i in range(0, len(text), 3):
        v = [IDX[text[i]], IDX[text[i + 1]], IDX[text[i + 2]]]
        for r in range(3):
            out.append(A_KR[(M[r][0] * v[0] + M[r][1] * v[1] + M[r][2] * v[2]) % 26])
    return "".join(out)


def normalize(text: str) -> str:
    return "".join(c for c in text.upper() if c.isalpha())


# ---- The eight constructions -------------------------------------------------
CONSTRUCTIONS = {
    "PK1": {
        "plaintext": (
            "Investigation log, item eight: knot, tightly-wound, its thread inscribed with letters."
            "The accession log says once unraveled it reveals the route to the lost archive of Pellegrin."
            "Twelve prior archivists tried to unravel it. All failed."),
        "encode": lambda p: q3_encode(p, "PROVENANCE"),
    },
    "PK2": {
        "plaintext": (
            "I have found references to the knot in seven other records in our archive."
            "The most intriguing is a passing comment in a treatise on textiles,"
            "written in Pellegrin's own hand, which says: un ago tanto sottile da leggere qualunque nodo."
            "I believed this to be just a turn of phrase, but the other mentions,"
            "scattered through marginalia in books that share no other topic,"
            "have led me to suspect the passage refers to a real object, a needle."),
        "encode": lambda p: colt_encode(p, "MARGINS"),
    },
    "PK3": {
        "plaintext": (
            "Seventh month. I wrote to fifteen correspondents in six countries,"
            "seeking any word of the item. Most knew nothing."
            "A few had heard legends of a needle fine enough to split a hair or pierce glass."
            "At last a Viennese anatomist said he saw such an instrument used at a surgical demonstration in Bern."
            "I wrote to his address. No answer came. I wrote again."),
        "encode": lambda p: q3_encode(q3_encode(p, "ORDINATE"), "PENTIMENTO"),
    },
    "PK4": {
        "plaintext": (
            "Two years in. The needle's trail led me to a craftsman named the Whitesmith."
            "On the road to his Alpine workshop I reread his perfunctory letters."
            "He met me at the gates and led me to a stone barn stacked with winter fodder."
            "One of his needles is hidden in the barn. I have begun to work."),
        "encode": lambda p: q3_encode(q3_encode(colt_encode(p, "UNDERLAY"), "OCHRE"), "VERDIGRIS"),
    },
    "PK5": {
        "plaintext": (
            "Fourteen days in the barn. I worked in the manner of an archivist:"
            "lifting each bale onto a cloth and examining the straws in rows."
            "The Whitesmith brought food and water but no counsel."
            "This morning, I felt the needle prick my finger, so fine that it drew no blood."
            "I carried it to the Whitesmith, and he took it from me and opened the inner door."),
        "encode": lambda p: q3_encode(colt_encode(p, "TWOYEARS"), "PK4KEY"),
    },
    "PK6": {
        "plaintext": (
            "The Whitesmith's workshop is filled with the old tools of his trade."
            "My eyes are drawn to the gutter along the wall, which is strewn with exquisite needles."
            "The Whitesmith says he makes one every day, and lost count long ago."
            "I ask what he does with them, and he says they are only the residue of his practice."
            "He tells me that if I study under him for ten years, he will let me take one of my own making."),
        "encode": lambda p: q3_encode(colt_encode(colt_encode(p, "HANDIWORK"), "SMITHWORK"), "PORTAL"),
    },
    "PK7": {
        "plaintext": (
            "Three weeks in. We rise before the sun, and each needle is done by noon."
            "The Whitesmith shows me his technique for purifying his metal before drawing it into a fine wire."
            "He has me repeat the same step four times, with slight variations. Still my hand falters."
            "I am patient, but I know this is not my calling. I have made peace with it and will go home soon."),
        "encode": lambda p: hill_encode(q3_encode(p, "ANNEAL"), "ALCHEMIST"),
    },
    "PK8": {
        "plaintext": (
            "I leave at midnight. Before going, I pick up one needle from the gutter."
            "I am grateful to my teacher, but the archive is my true calling, and the knot awaits."
            "I leave the Whitesmith a short letter."),
        "encode": lambda p: q3_encode(q3_encode(q3_encode(q3_encode(p, "METE"), "METER"), "METIER"), "MASTERY"),
    },
}

# PK5's substitution key is the entire PK4 plaintext (normalized).
PK4_KEY = normalize(CONSTRUCTIONS["PK4"]["plaintext"])
CONSTRUCTIONS["PK5"]["encode"] = lambda p: q3_encode(colt_encode(p, "TWOYEARS"), PK4_KEY)


def main() -> None:
    official = json.loads((ROOT / "pk_all_ciphertexts.json").read_text())
    repo = json.loads((ROOT / "pk_verified_solutions.json").read_text())

    print(f"{'ID':4} {'len':>4} {'official CT':>12} {'repo PT was':>12}  construction")
    for pk, spec in CONSTRUCTIONS.items():
        pt = normalize(spec["plaintext"])
        ct = spec["encode"](pt)
        ok = ct == official[pk]
        old_ok = repo.get(pk, {}).get("plaintext") == pt
        print(f"{pk:4} {len(pt):4} {'MATCH' if ok else 'MISMATCH':>12} "
              f"{'correct' if old_ok else 'WAS WRONG':>12}  "
              f"{len(pt)} chars, sha-match={ok}")
        if not ok:
            print("   computed:", ct[:60])
            print("   official:", official[pk][:60])

    # also verify repo ciphertexts match official
    for pk in CONSTRUCTIONS:
        assert repo[pk]["ciphertext"] == official[pk], f"{pk} repo CT differs from official CT"
    print("\nAll repo-recorded ciphertexts match the official ones.")


if __name__ == "__main__":
    main()
