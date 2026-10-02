#!/usr/bin/env python3
"""Empirically pin down the Paradigm Kryptos transposition convention.

PK2 is a pure T(7) with key MARGINS and a verified plaintext/ciphertext pair.
We try every plausible route convention and report which ones reproduce the
official ciphertext exactly.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REC = json.loads((ROOT / "pk_verified_solutions.json").read_text())["PK2"]
PT = REC["plaintext"]
CT = REC["ciphertext"]
KEY = "MARGINS"
N, W = len(PT), 7
H = N // W
assert len(PT) == len(CT) == 350


def key_order(key: str) -> list[int]:
    """Column indices in alphabetical order of the keyword letters."""
    return sorted(range(len(key)), key=lambda i: (key[i], i))


ORDER = key_order(KEY)
print("N,W,H:", N, W, H)
print("alphabetical column order of MARGINS:", ORDER)


def write_rows_read_cols_by_key(pt: str) -> str:
    """Standard columnar: fill row-wise, read columns in key order."""
    grid = [pt[r * W:(r + 1) * W] for r in range(H)]
    out = []
    for c in ORDER:
        out.extend(grid[r][c] for r in range(H))
    return "".join(out)


def write_rows_read_cols_by_index(pt: str) -> str:
    """Fill row-wise; output block k = column ORDER[k] (same as above)."""
    return write_rows_read_cols_by_key(pt)


def write_cols_read_rows_by_key(pt: str) -> str:
    """Site description: write in columns, swap columns, read by rows."""
    cols = [pt[c * H:(c + 1) * H] for c in range(W)]
    perm = [cols[c] for c in ORDER]          # perm[k] = column now in slot k
    out = []
    for r in range(H):
        out.extend(perm[c][r] for c in range(W))
    return "".join(out)


def write_cols_read_cols_by_key(pt: str) -> str:
    """Fill column-wise; output is the columns concatenated in key order."""
    cols = [pt[c * H:(c + 1) * H] for c in range(W)]
    out = []
    for c in ORDER:
        out.extend(cols[c])
    return "".join(out)


def write_rows_read_rows_by_key(pt: str) -> str:
    """Fill row-wise; reorder each row's letters so columns land in key order."""
    grid = [pt[r * W:(r + 1) * W] for r in range(H)]
    out = []
    for r in range(H):
        out.extend(grid[r][c] for c in ORDER)
    return "".join(out)


CONVENTIONS = {
    "A: write rows, read columns (key order)  [classic columnar]": write_rows_read_cols_by_key,
    "B: write cols, swap cols, read rows      [site description]": write_cols_read_rows_by_key,
    "C: write cols, read cols (key order)     [block permutation]": write_cols_read_cols_by_key,
    "D: write rows, read rows (key order)": write_rows_read_rows_by_key,
}

for name, fn in CONVENTIONS.items():
    got = fn(PT)
    match = sum(a == b for a, b in zip(got, CT))
    print(f"{name}: match {match}/{N} {'EXACT' if got == CT else ''}")

print("\nCT head:", CT[:40])
for name, fn in CONVENTIONS.items():
    print(f"{name[:1]} head:", fn(PT)[:40])
