#!/usr/bin/env python3
"""Spectral (phase) attack on the rotating-alphabet cipher.

Under the model the transition-count matrix of the ciphertext satisfies

    M[a][b]  ~=  n * q[ alpha_b - alpha_a ]        (mod 26)

i.e. M is a permuted circulant: M = P C P^T with C[x][y] = q(y-x).
The eigenvectors of a circulant are the Fourier vectors f_k[x] = w^(k x), so
the eigenvectors of M are v_k[a] = w^(k*alpha_a): constant modulus, with
phases linear in alpha.  That gives a direct, cheap route to alpha:
take the phases of an eigenvector, divide by the candidate mode k, round,
and keep whatever is a permutation with a good circulant residual.
"""
from __future__ import annotations

import numpy as np

import common as C

W26 = np.exp(2j * np.pi / 26.0)


def transition_counts(ct: str) -> np.ndarray:
    idx = C.to_idx(ct)
    M = np.zeros((26, 26), dtype=np.float64)
    np.add.at(M, (idx[:-1], idx[1:]), 1.0)
    return M


def circulant_residual(M: np.ndarray, alpha: np.ndarray) -> float:
    """Profile-likelihood residual of the circulant fit for this necklace."""
    a, b = np.nonzero(M)
    d = (alpha[b] - alpha[a]) % 26
    w = M[a, b]
    tot = np.bincount(d, weights=w, minlength=26)
    cnt = np.bincount(d, minlength=26).astype(float)
    g = np.divide(tot, cnt, out=np.zeros(26), where=cnt > 0)  # mean per class
    pred = g[d]
    return float(((w - pred) ** 2).sum() / max(1.0, (w ** 2).sum()))


def loglik(M: np.ndarray, alpha: np.ndarray) -> float:
    """Poisson-style profile log-likelihood (maximise)."""
    a, b = np.nonzero(M)
    d = (alpha[b] - alpha[a]) % 26
    w = M[a, b]
    tot = np.bincount(d, weights=w, minlength=26)
    cnt = np.bincount(d, minlength=26).astype(float)
    g = np.divide(tot, cnt, out=np.zeros(26), where=cnt > 0)
    g = np.maximum(g, 1e-9)
    return float((w * np.log(g[d])).sum())


def spectral_candidates(ct: str, top_k: int = 14, modulus_tol: float = 0.9):
    M = transition_counts(ct)
    vals, vecs = np.linalg.eig(M)
    order = np.argsort(-np.abs(vals))
    out = []
    for rank in order[:top_k]:
        v = vecs[:, rank]
        mod = np.abs(v)
        if mod.mean() == 0 or mod.std() / mod.mean() > modulus_tol:
            continue                       # not a clean Fourier mode
        phase = np.angle(v)
        for k in range(1, 26):
            alpha = np.round((phase * 26.0 / (2 * np.pi * k)) % 26).astype(np.int64) % 26
            if len(set(alpha.tolist())) != 26:
                continue
            out.append((rank, k, alpha))
    return M, out


def hc_refine(M: np.ndarray, alpha: np.ndarray, sweeps: int = 200):
    """Hill-climb the circulant fit (swap moves)."""
    cur = loglik(M, alpha)
    for _ in range(sweeps):
        improved = False
        for a in range(26):
            for b in range(a + 1, 26):
                alpha[a], alpha[b] = alpha[b], alpha[a]
                v = loglik(M, alpha)
                if v > cur:
                    cur = v
                    improved = True
                else:
                    alpha[a], alpha[b] = alpha[b], alpha[a]
        if not improved:
            break
    return cur, alpha


def attack(ct: str, refine_rounds: int = 40):
    M, cands = spectral_candidates(ct)
    best = None
    seen = set()
    for rank, k, alpha in cands:
        sig = tuple((alpha - alpha[0]) % 26)
        sig = min(sig, tuple((-np.array(sig)) % 26))
        if sig in seen:
            continue
        seen.add(sig)
        sc, refined = hc_refine(M, alpha.copy())
        if best is None or sc > best[0]:
            best = (sc, refined, (rank, k))
    return M, best
