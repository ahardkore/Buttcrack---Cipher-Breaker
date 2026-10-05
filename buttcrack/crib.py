"""Simple additive crib-dragging worksheet helpers."""

from __future__ import annotations

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def implied_shifts(
    ciphertext: str,
    crib: str,
    offset: int,
    alphabet: str = ALPHABET,
    mode: str = "vigenere",
) -> list[int | None]:
    """Derive implied keystream shifts for a crib aligned at a specific offset."""
    c = "".join(x for x in ciphertext.upper() if x in alphabet)
    p = "".join(x for x in crib.upper() if x in alphabet)
    out: list[int | None] = [None] * len(p)
    if offset < 0 or offset + len(p) > len(c):
        return out
    m = len(alphabet)
    for i, (cc, pp) in enumerate(zip(c[offset : offset + len(p)], p)):
        c_idx = alphabet.index(cc)
        p_idx = alphabet.index(pp)
        if mode == "vigenere":
            out[i] = (c_idx - p_idx) % m
        elif mode == "beaufort":
            out[i] = (c_idx + p_idx) % m
        elif mode == "variant_beaufort":
            out[i] = (p_idx - c_idx) % m
        else:
            raise ValueError(f"Unknown mode: {mode}")
    return out


def consistent_period(shifts: list[int | None], period: int) -> bool:
    """Check whether a single contiguous sequence of shifts is consistent with a given period."""
    by_residue: dict[int, int] = {}
    for i, shift in enumerate(shifts):
        if shift is None:
            continue
        residue = i % period
        if residue in by_residue and by_residue[residue] != shift:
            return False
        by_residue[residue] = shift
    return True


def multi_crib_consistent_period(
    anchors: dict[int, str],
    ciphertext: str,
    period: int,
    alphabet: str = ALPHABET,
    mode: str = "vigenere",
) -> bool:
    """Check whether multiple disjoint cribs at fixed absolute offsets are mutually consistent.

    Parameters
    ----------
    anchors:
        Dictionary mapping absolute 0-indexed positions to plaintext characters (or strings).
    ciphertext:
        Full ciphertext string.
    period:
        Candidate repeating key period.
    alphabet:
        Character alphabet (e.g. standard A-Z or KRYPTOS-keyed).
    mode:
        Encipherment convention ('vigenere', 'beaufort', 'variant_beaufort').
    """
    m = len(alphabet)
    by_residue: dict[int, int] = {}
    for pos, pt in anchors.items():
        for j, p_char in enumerate(pt):
            abs_pos = pos + j
            if abs_pos >= len(ciphertext):
                continue
            c_char = ciphertext[abs_pos]
            if c_char not in alphabet or p_char not in alphabet:
                continue
            c_idx = alphabet.index(c_char)
            p_idx = alphabet.index(p_char)

            if mode == "vigenere":
                shift = (c_idx - p_idx) % m
            elif mode == "beaufort":
                shift = (c_idx + p_idx) % m
            elif mode == "variant_beaufort":
                shift = (p_idx - c_idx) % m
            else:
                raise ValueError(f"Unknown mode: {mode}")

            residue = abs_pos % period
            if residue in by_residue and by_residue[residue] != shift:
                return False
            by_residue[residue] = shift
    return True

