"""Simple additive crib-dragging worksheet helpers."""
from __future__ import annotations
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
def implied_shifts(ciphertext: str, crib: str, offset: int) -> list[int | None]:
    c = "".join(x for x in ciphertext.upper() if x in ALPHABET)
    p = "".join(x for x in crib.upper() if x in ALPHABET)
    out: list[int | None] = [None] * len(p)
    if offset < 0 or offset + len(p) > len(c): return out
    for i, (cc, pp) in enumerate(zip(c[offset:offset + len(p)], p)):
        out[i] = (ALPHABET.index(cc) - ALPHABET.index(pp)) % 26
    return out
def consistent_period(shifts: list[int | None], period: int) -> bool:
    by_residue: dict[int, int] = {}
    for i, shift in enumerate(shifts):
        if shift is None: continue
        residue = i % period
        if residue in by_residue and by_residue[residue] != shift: return False
        by_residue[residue] = shift
    return True
