#!/usr/bin/env python3
"""HILL CIPHER TEST - derived purely from public sculpture evidence
(the extra L making HILL in the tableau's rightmost column, per the
Bauer-Link-Molle conjecture). No plaintext assumed beyond the four
artist-confirmed anchor words.

2x2 Hill: solve the key matrix from every pair of known aligned blocks,
verify against ALL known blocks; if a matrix survives, decrypt K4.
3x3 Hill: check the fatal duplicate-plaintext-block test."""

import itertools, math

STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
KRY = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
K4_CT = ("OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJ"
         "KLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR")
ANCH = {**{22+i: c for i, c in enumerate("EAST")},
        **{26+i: c for i, c in enumerate("NORTHEAST")},
        **{64+i: c for i, c in enumerate("BERLIN")},
        **{70+i: c for i, c in enumerate("CLOCK")}}

def idx(alpha):
    return {c: i for i, c in enumerate(alpha)}

def aligned_blocks(alpha, n):
    """blocks of size n aligned from position 1; keep only fully-known ones."""
    out = []
    for start in range(1, 98, n):
        pos = list(range(start, start + n))
        if pos[-1] > 97:
            break
        if all(p in ANCH for p in pos):
            pt = tuple(idx(alpha)[ANCH[p]] for p in pos)
            ct = tuple(idx(alpha)[K4_CT[p-1]] for p in pos)
            out.append((pos[0], pt, ct))
    return out

# ---------- 3x3: duplicate-plaintext contradiction test ------------------
print("=" * 72)
print("3x3 HILL - same plaintext block must give same ciphertext block")
print("=" * 72)
for alpha, name in ((STD, "std"), (KRY, "KRYPTOS")):
    for shift in (0, 1, 2):  # three possible alignments
        blocks = []
        for start in range(1 + shift, 98, 3):
            pos = list(range(start, start + 3))
            if pos[-1] > 97:
                break
            if all(p in ANCH for p in pos):
                blocks.append((tuple(idx(alpha)[ANCH[p]] for p in pos),
                               tuple(idx(alpha)[K4_CT[p-1]] for p in pos)))
        seen, clash = {}, None
        for pt, ct in blocks:
            if pt in seen and seen[pt] != ct:
                clash = (pt, seen[pt], ct); break
            seen[pt] = ct
        verdict = ("CONTRADICTION: plaintext block %s encrypts to both %s and %s"
                   % clash if clash else
                   f"ok ({len(blocks)} fully-known blocks, no clash)")
        print(f"  [{name}] alignment offset {shift}: {verdict}")

# ---------- 2x2: solve and verify ----------------------------------------
def mat_mul(A, B, m=26):
    return [[sum(A[i][k] * B[k][j] for k in range(2)) % m for j in range(2)]
            for i in range(2)]

def mat_inv(P, m=26):
    det = (P[0][0] * P[1][1] - P[0][1] * P[1][0]) % m
    if math.gcd(det, m) != 1:
        return None
    dinv = pow(det, -1, m)
    return [[P[1][1] * dinv % m, -P[0][1] * dinv % m],
            [-P[1][0] * dinv % m, P[0][0] * dinv % m]]

def vec(M, v, m=26):
    return tuple(sum(M[i][k] * v[k] for k in range(2)) % m for i in range(2))

BIGRAMS = list(set(("TH HE IN ER AN RE ON AT ND ST ES EN OF TE ED OR TI HI "
                    "AS TO AL AR BE EA EE HA IS IT LE ME NG NT OU RA SE VE WA").split()))
def score(t):
    t = "".join(ch for ch in t if ch.isalpha())
    bg = [t[i:i+2] for i in range(len(t) - 1)]
    return sum(b in BIGRAMS for b in bg) / len(bg) if bg else 0

print()
print("=" * 72)
print("2x2 HILL - solve M from every pair of known blocks, verify on all")
print("=" * 72)
for alpha, name in ((STD, "std"), (KRY, "KRYPTOS")):
    blocks = aligned_blocks(alpha, 2)
    print(f"\n[{name}] {len(blocks)} fully-known aligned blocks:",
          ["%d:%s->%s" % (s, "".join(alpha[x] for x in pt),
                          "".join(alpha[x] for x in ct))
           for s, pt, ct in blocks][:4], "...")
    survivors = []
    for (s1, p1, c1), (s2, p2, c2) in itertools.combinations(blocks, 2):
        for convention in ("col", "row"):     # C = M.P  or  C = P.M
            Pm = [[p1[0], p2[0]], [p1[1], p2[1]]] if convention == "col" \
                 else [[p1[0], p1[1]], [p2[0], p2[1]]]
            inv = mat_inv(Pm)
            if inv is None:
                continue
            Cm = [[c1[0], c2[0]], [c1[1], c2[1]]] if convention == "col" \
                 else [[c1[0], c1[1]], [c2[0], c2[1]]]
            M = mat_mul(Cm, inv) if convention == "col" else mat_mul(inv, Cm)
            ok = True
            for s, p, c in blocks:
                got = vec(M, p) if convention == "col" else vec(
                    [[M[0][0], M[1][0]], [M[0][1], M[1][1]]], p)
                if got != c:
                    ok = False; break
            if ok:
                survivors.append((convention, M))
    if not survivors:
        print(f"[{name}] NO 2x2 matrix satisfies all anchor blocks.")
    else:
        seen = set()
        for conv, M in survivors:
            key = (conv, tuple(map(tuple, M)))
            if key in seen:
                continue
            seen.add(key)
            print(f"[{name}] SURVIVING MATRIX ({conv}): {M}")
            # decrypt K4: invert M, apply to each aligned block
            Minv = mat_inv(M)
            out = []
            for start in range(1, 97, 2):
                c = (idx(alpha)[K4_CT[start-1]], idx(alpha)[K4_CT[start]])
                if conv == "col":
                    p = vec(Minv, c)
                else:
                    p = vec([[Minv[0][0], Minv[1][0]],
                             [Minv[0][1], Minv[1][1]]], c)
                out += [alpha[p[0]], alpha[p[1]]]
            dec = "".join(out) + K4_CT[96]
            print(f"  decryption: {dec}")
            print(f"  score {score(dec):.3f}")
print("\nDONE.")
