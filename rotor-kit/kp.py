#!/usr/bin/env python3
"""Known-plaintext key recovery for the rotating-alphabet cipher.

Identity used (derived from the algorithm):

    c_k = B[ (s0 + sum_{j<=k} t_j) mod 26 ],   t_j = pos_T(p_j)

so with alpha = B^-1:

    alpha(c_k) - alpha(c_{k-1}) = t_k = T(p_k)        (mod 26)

and therefore, for any i<j with c_i == c_j:

    sum_{i<t<=j} T(p_t) == 0        (mod 26)

Those are linear equations in the 26 unknown values T(p).  Solve them over
Z_26 (CRT of Z_2 and Z_13), keep every solution where T and alpha are both
bijections, and verify by re-encryption.
"""
from __future__ import annotations

import itertools
from collections import defaultdict

import numpy as np

import common as C


def _letter_class_sums(ct, pt):
    """Rows of the linear system: for each ciphertext letter, the intervals
    between consecutive occurrences contribute 'counts of plaintext letters
    in the interval, mod 26' summing to 0."""
    rows = defaultdict(set)          # plaintext letter -> positions
    occ = defaultdict(list)          # ciphertext letter -> positions
    for i, (c, p) in enumerate(zip(ct, pt)):
        rows[p].add(i)
        occ[c].append(i)
    eqs = []
    for c, pos in occ.items():
        for a, b in zip(pos, pos[1:]):
            counts = defaultdict(int)
            for p, plist in rows.items():
                counts[p] += sum(1 for x in range(a + 1, b + 1) if x in plist)
            if any(counts.values()):
                eqs.append(counts)
    return eqs


def _rref_mod(A, p):
    A = (A % p).astype(np.int64)
    m, n = A.shape
    r = 0
    pivots = []
    for c in range(n):
        piv = None
        for i in range(r, m):
            if A[i, c] % p:
                piv = i
                break
        if piv is None:
            continue
        if piv != r:
            A[[r, piv]] = A[[piv, r]]
        inv = pow(int(A[r, c]), -1, p)
        A[r] = (A[r] * inv) % p
        col = A[:, c].copy()
        for i in range(m):
            if i != r and col[i] % p:
                A[i] = (A[i] - col[i] * A[r]) % p
        pivots.append(c)
        r += 1
        if r == m:
            break
    return A, pivots


def _nullspace_mod(A, p):
    R, piv = _rref_mod(A, p)
    free = [c for c in range(A.shape[1]) if c not in piv]
    basis = []
    for f in free:
        v = np.zeros(A.shape[1], dtype=np.int64)
        v[f] = 1
        for i, c in enumerate(piv):
            v[c] = (-R[i, f]) % p
        basis.append(v % p)
    return basis


def _crt(x, y):
    """Combine mod 2 (x) and mod 13 (y) into mod 26."""
    for t in range(26):
        if t % 2 == x and t % 13 == y:
            return t
    raise AssertionError


def solve_kp(ct, pt, max_candidates=2_000_000):
    """Recover key material from known plaintext aligned with the ciphertext.

    Returns a list of dicts:
        tau     -- {plaintext letter: T-value} recovered (mod 26)
        alpha   -- {ciphertext letter: B^-1 value} recovered
        complete-- True when all 26 plaintext letters were covered and the
                   key verifies against the whole ciphertext
        key     -- (top, bottom) when complete
    """
    ct = "".join(ch for ch in ct.upper() if ch.isalpha())
    pt = "".join(ch for ch in pt.upper() if ch.isalpha())
    n = min(len(ct), len(pt))
    ct, pt = ct[:n], pt[:n]
    letters = sorted(set(pt))
    idx = {ch: i for i, ch in enumerate(letters)}
    eqs = _letter_class_sums(ct, pt)
    A = np.zeros((len(eqs), len(letters)), dtype=np.int64)
    for r, counts in enumerate(eqs):
        for ch, k in counts.items():
            if ch in idx:
                A[r, idx[ch]] = k % 26

    b13 = _nullspace_mod(A, 13)
    b2 = _nullspace_mod(A, 2)
    d13, d2 = len(b13), len(b2)
    if 13 ** d13 * 2 ** d2 > max_candidates:
        raise RuntimeError(f"solution space too large: 13^{d13} * 2^{d2} "
                           f"(need longer known plaintext)")
    out = []
    for combo13 in itertools.product(range(13), repeat=d13):
        v13 = np.zeros(len(letters), dtype=np.int64)
        for coeff, vec in zip(combo13, b13):
            v13 = (v13 + coeff * vec) % 13
        for combo2 in itertools.product(range(2), repeat=d2):
            v2 = np.zeros(len(letters), dtype=np.int64)
            for coeff, vec in zip(combo2, b2):
                v2 = (v2 + coeff * vec) % 2
            tau = np.array([_crt(int(a), int(b)) for a, b in zip(v2, v13)])
            if len(set(tau.tolist())) != len(letters):
                continue
            rec = _reconstruct(ct, pt, letters, tau)
            if rec:
                out.append(rec)
    return out


def _reconstruct(ct, pt, letters, tau):
    """Walk the ciphertext, derive alpha, and assemble whatever key is known."""
    tval = {ch: int(v) for ch, v in zip(letters, tau)}
    alpha = {}
    acc = 0
    for c, p in zip(ct, pt):
        acc = (acc + tval[p]) % 26
        if c not in alpha:
            alpha[c] = acc
        elif alpha[c] != acc:
            return None
    if len(set(alpha.values())) != len(alpha):
        return None
    rec = {"tau": dict(tval), "alpha": alpha, "complete": False,
           "coverage": len(letters), "letters": letters, "key": None}
    if len(letters) == 26 and len(set(tau.tolist())) == 26:
        if len(alpha) < 26:
            return rec  # all T known but not every cipher letter was seen
        top = "".join({int(v): ch for ch, v in zip(letters, tau)}[i] for i in range(26))
        bottom = ["?"] * 26
        for ch, v in alpha.items():
            bottom[v] = ch
        if "?" in bottom:
            return rec
        bottom_s = "".join(bottom)
        # verify against the full ciphertext, not just the crib
        if C.encrypt_text(pt, top, bottom_s)[: len(pt)] != ct[: len(pt)]:
            return None
        rec.update(complete=True, key=(top, bottom_s))
    return rec
