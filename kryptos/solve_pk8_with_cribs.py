#!/usr/bin/env python3
"""Exact additive crib-solver for PK8 and PK9 on KRYPTOS alphabet.
Using diid's exact Gaussian elimination over GF(2) and GF(13).
"""

import json
from collections import Counter
from math import gcd, isqrt, lcm

KRYPTOS_ALPHABET = "KRYPTOSABCDEFGHIJLMNQUVWXZ"

def _periods(periods):
    return tuple(periods)

def _row(position, periods):
    return [int(j == position % p) for p in periods for j in range(p)]

class _System:
    def __init__(self, prime):
        self.prime = prime
        self.basis = {}

    def reduce(self, row):
        row = [x % self.prime for x in row]
        value = 0
        for pivot in sorted(self.basis):
            factor = row[pivot]
            if factor:
                known, rhs = self.basis[pivot]
                row = [(a - factor * b) % self.prime for a, b in zip(row, known)]
                value = (value + factor * rhs) % self.prime
        return row, value

    def add(self, row, value):
        row, known = self.reduce(row)
        rhs = (value - known) % self.prime
        pivot = next((j for j, x in enumerate(row) if x), None)
        if pivot is None:
            return rhs == 0
        inverse = pow(row[pivot], -1, self.prime)
        self.basis[pivot] = ([x * inverse % self.prime for x in row], rhs * inverse % self.prime)
        return True

    def determined(self, row):
        remaining, value = self.reduce(row)
        return None if any(remaining) else value

    def representative(self, width):
        out = [0] * width
        for pivot in sorted(self.basis, reverse=True):
            row, rhs = self.basis[pivot]
            out[pivot] = (rhs - sum(a * b for a, b in zip(row, out))) % self.prime
        return out

def solve_additive_crib(ciphertext, periods, fragments, alphabet=KRYPTOS_ALPHABET):
    ps = _periods(periods)
    ct = ciphertext.upper()
    index = {c: i for i, c in enumerate(alphabet)}
    constraints = []
    for start, text in fragments:
        crib = text.upper()
        constraints.extend((start + j, c) for j, c in enumerate(crib))
    
    systems = [_System(2), _System(13)]
    conflicts = []
    for number, (position, char) in enumerate(constraints):
        rhs = (index[ct[position]] - index[char]) % 26
        for system in systems:
            if not system.add(_row(position, ps), rhs):
                conflicts.append((position, char, system.prime))
    
    if conflicts:
        return {"consistent": False, "conflicts": conflicts}
    
    pad = []
    for position in range(len(ct)):
        values = [s.determined(_row(position, ps)) for s in systems]
        a, b = values
        pad.append(None if a is None or b is None else (13 * a + 14 * b) % 26)
    
    x2, x13 = [s.representative(sum(ps)) for s in systems]
    representative = [(13 * a + 14 * b) % 26 for a, b in zip(x2, x13)]
    
    keys = []
    offset = 0
    for period in ps:
        keys.append(representative[offset : offset + period])
        offset += period
        
    determined = [i for i, value in enumerate(pad) if value is not None]
    pt = "".join("?" if value is None else alphabet[(index[c] - value) % 26] for c, value in zip(ct, pad))
    
    return {
        "consistent": True,
        "determined_count": len(determined),
        "status": "determined" if len(determined) == len(ct) else "partial",
        "keystream": pad,
        "plaintext": pt,
        "representative_keys": keys,
        "ranks": (len(systems[0].basis), len(systems[1].basis))
    }

def drag_crib(ciphertext, periods, crib, alphabet=KRYPTOS_ALPHABET):
    L = len(crib)
    matches = []
    for pos in range(len(ciphertext) - L + 1):
        res = solve_additive_crib(ciphertext, periods, [(pos, crib)], alphabet=alphabet)
        if res["consistent"]:
            matches.append((pos, res["determined_count"], res["plaintext"], res["ranks"]))
    return matches

if __name__ == "__main__":
    with open("pk_all_ciphertexts.json") as f:
        ciphers = json.load(f)
    
    ct8 = ciphers["PK8"]
    print(f"Loaded PK8: len={len(ct8)}")
    
    # Test a few narrative cribs
    cribs = [
        "THEWHITESMITH", "WHITESMITHS", "INTHEWORKSHOP", "EXQUISITENEEDLE",
        "STUDYUNDERHIM", "FORTENYEARS", "OFMYOWNMAKING", "INVESTIGATION",
        "SEVENTHMONTH", "FIFTEENCORRESPONDENTS", "SURGICALDEMONSTRATION",
        "VIENNESEANATOMIST", "SPLITAHAIR", "PIERCEGLASS", "FIRSTTIME",
        "FORTHEFIRSTTIME", "ATLASTTHEFIRE", "THEFIREWASLIT", "HAMMERANDANVIL"
    ]
    
    for c in cribs:
        m = drag_crib(ct8, [4, 5, 6, 7], c)
        if m:
            print(f"Crib '{c}' (len {len(c)}): {len(m)} consistent placements:")
            for pos, det, pt, ranks in m[:5]:
                print(f"   pos {pos:3d} | det {det:3d}/153 | ranks {ranks}: {pt[:60]}...")
