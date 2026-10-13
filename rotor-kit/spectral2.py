#!/usr/bin/env python3
"""Pooled spectral attack: M_k (pairs at skip k) are all permuted circulants
with the SAME eigenvectors, so their sum has ~k x the data on the same phases."""
from __future__ import annotations

import numpy as np
import common as C


def skip_matrix(ct: str, k: int) -> np.ndarray:
    idx = C.to_idx(ct)
    M = np.zeros((26, 26))
    np.add.at(M, (idx[:-k], idx[k:]), 1.0)
    return M


def pooled_matrices(ct: str, K: int):
    return [skip_matrix(ct, k) for k in range(1, K + 1)]


def combined_loglik(ms, alpha):
    tot = 0.0
    for M in ms:
        a, b = np.nonzero(M)
        d = (alpha[b] - alpha[a]) % 26
        w = M[a, b]
        cnt = np.bincount(d, minlength=26).astype(float)
        s = np.bincount(d, weights=w, minlength=26)
        g = np.maximum(np.divide(s, cnt, out=np.zeros(26), where=cnt > 0), 1e-9)
        tot += float((w * np.log(g[d])).sum())
    return tot


def hc(ms, alpha, sweeps=60):
    cur = combined_loglik(ms, alpha)
    for _ in range(sweeps):
        improved = False
        for a in range(26):
            for b in range(a + 1, 26):
                alpha[a], alpha[b] = alpha[b], alpha[a]
                v = combined_loglik(ms, alpha)
                if v > cur:
                    cur, improved = v, True
                else:
                    alpha[a], alpha[b] = alpha[b], alpha[a]
        if not improved:
            break
    return cur, alpha


def candidates_from_eigs(S, keep=10):
    vals, vecs = np.linalg.eig(S)
    order = np.argsort(-np.abs(vals))
    out = []
    for rank in order[:keep]:
        v = vecs[:, rank]
        mod = np.abs(v)
        if mod.mean() <= 0 or mod.std() / mod.mean() > 1.2:
            continue
        phase = np.angle(v)
        for k in range(1, 26):
            alpha = np.round((phase * 26.0 / (2 * np.pi * k)) % 26).astype(np.int64) % 26
            if len(set(alpha.tolist())) == 26:
                out.append((rank, k, alpha))
    return out


def attack(ct, K=4, keep=10, refine=True):
    ms = pooled_matrices(ct, K)
    S = sum(ms)
    cands = candidates_from_eigs(S, keep)
    results = []
    seen = set()
    for rank, k, alpha in cands:
        sig = tuple((alpha - alpha[0]) % 26)
        sig = min(sig, tuple((-np.array(sig)) % 26))
        if sig in seen:
            continue
        seen.add(sig)
        if refine:
            sc, a2 = hc(ms, alpha.copy())
        else:
            sc, a2 = combined_loglik(ms, alpha), alpha
        results.append((sc, a2, (rank, k)))
    results.sort(key=lambda r: -r[0])
    return ms, results


def diagnostics(ct, K=4, keep=6):
    ms = pooled_matrices(ct, K)
    S = sum(ms)
    vals, vecs = np.linalg.eig(S)
    order = np.argsort(-np.abs(vals))
    lines = []
    for rank in order[:keep]:
        v = vecs[:, rank]
        mod = np.abs(v)
        ratio = mod.std() / mod.mean() if mod.mean() else 9.9
        phase = np.angle(v)
        line = f"eig {abs(vals[rank]):7.2f} modulus std/mean={ratio:5.2f}"
        # best rounding distance is unknown without truth; show phase spread
        lines.append(line)
    return lines
