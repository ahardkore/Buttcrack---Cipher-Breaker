#!/usr/bin/env python3
"""
Fast solver for the rotating-alphabet (self-rotating necklace) cipher.

Model (see common.py): with u[letter] = position of the letter on the hidden
necklace, the plaintext satisfies

    p_k = T[ (u[c_k] - u[c_{k-1}]) mod 26 ]

where T is an arbitrary substitution.  So for a fixed necklace u the d-sequence
is a classical substitution cryptogram, and the *quality of the best crack* is
the objective to climb.

Modes:
    basin   -- how close to the truth must a start be for HC to recover it?
    bench   -- synthetic 409-letter benchmark with a known key
    real    -- run the real challenge ciphertext
"""
from __future__ import annotations

import argparse
import json
import math
import random
import time
from pathlib import Path

import numpy as np

import common as C

WORK = Path("/home/user/rotor-attack")

# ---------------------------------------------------------------------- solver


class Fast:
    """Vectorised objective machinery for a fixed ciphertext."""

    def __init__(self, ct: str):
        self.ct = ct.upper()
        self.c = C.to_idx(self.ct)
        self.n = len(self.c)
        self.c0 = self.c[:-1]
        self.c1 = self.c[1:]
        # log-english tables
        self.LU = C.LOG_UNI_MAT
        self.LB = C.LOG_BI_MAT
        # sparse helpers
        self.uni_desc = np.sort(C.ENGLISH_FREQ_PCT / C.ENGLISH_FREQ_PCT.sum())[::-1]
        # cache
        self._cache: dict[tuple, tuple] = {}

    # -- distances ------------------------------------------------------ #
    def dist(self, u: np.ndarray) -> np.ndarray:
        return (u[self.c1] - u[self.c0]) % 26

    # -- objective 1: proper joint likelihood (cheap) -------------------- #
    def joint_ll(self, u: np.ndarray) -> float:
        d = self.dist(u)
        dist = np.bincount(d, minlength=26).astype(np.float64)
        order = np.argsort(-dist, kind="stable")
        qorder = np.argsort(-C.ENGLISH_FREQ_PCT, kind="stable")
        sigma = np.empty(26, dtype=np.int64)
        sigma[order] = qorder
        val = float(dist @ self.LU[sigma])
        codes = d[:-1] * 26 + d[1:]
        Q = np.bincount(codes, minlength=676)
        nz = np.nonzero(Q)[0]
        i, j = nz // 26, nz % 26
        val += float(Q[nz] @ self.LB[sigma[i], sigma[j]])
        return val

    # -- objective 2: the best achievable crack score (expensive, exact) - #
    def _windows_by_val(self, d: np.ndarray):
        n = len(d)
        m = n - 3
        wins = []
        for v in range(26):
            pos = np.nonzero(d == v)[0]
            if pos.size == 0:
                wins.append(np.empty(0, dtype=np.int64))
                continue
            starts = np.concatenate([np.arange(max(0, p - 3), min(m, p + 1))
                                     for p in pos]) if pos.size else np.empty(0, dtype=np.int64)
            wins.append(np.unique(starts))
        return wins

    def crack(self, u: np.ndarray, sigma0: np.ndarray | None = None,
              max_sweeps: int = 14, early_cutoff: float | None = None):
        """Hill-climb theta on d(u) with exact incremental quadgram deltas."""
        d = self.dist(u)
        if sigma0 is None:
            dist = np.bincount(d, minlength=26).astype(np.float64)
            order = np.argsort(-dist, kind="stable")
            qorder = np.argsort(-C.ENGLISH_FREQ_PCT, kind="stable")
            sigma = np.empty(26, dtype=np.int64)
            sigma[order] = qorder
        else:
            sigma = sigma0.copy()
        pos_by_val = [np.nonzero(d == v)[0] for v in range(26)]
        wins = self._windows_by_val(d)
        t = sigma[d]
        cur = C.qg_score(t)
        best, best_sigma = cur, sigma.copy()
        pairs = [(i, j) for i in range(26) for j in range(i + 1, 26)]
        for sweep in range(max_sweeps):
            improved = False
            for i, j in pairs:
                idx = np.concatenate((pos_by_val[i], pos_by_val[j]))
                if idx.size == 0:
                    continue
                k = wins[i] if wins[j].size == 0 else (
                    wins[j] if wins[i].size == 0 else np.unique(np.concatenate((wins[i], wins[j]))))
                if k.size == 0:
                    continue
                old = float(C.QG[t[k] * 17576 + t[k+1] * 676 + t[k+2] * 26 + t[k+3]].sum())
                sigma[i], sigma[j] = sigma[j], sigma[i]
                t[idx] = sigma[d[idx]]
                new = float(C.QG[t[k] * 17576 + t[k+1] * 676 + t[k+2] * 26 + t[k+3]].sum())
                if new > old:
                    cur += new - old
                    improved = True
                else:
                    sigma[i], sigma[j] = sigma[j], sigma[i]
                    t[idx] = sigma[d[idx]]
            if cur > best:
                best, best_sigma = cur, sigma.copy()
            if not improved:
                break
            if early_cutoff is not None and sweep >= 1 and best < early_cutoff:
                break
        return best, best_sigma

    # -- decode/encode -------------------------------------------------- #
    def text(self, u, sigma) -> str:
        d = self.dist(u)
        return C.to_text(sigma[d])


# ----------------------------------------------------------------- metaheuristic

def hc(fast: Fast, u0, mode="joint", max_sweeps=200, rng=None, warm=None):
    rng = rng or random.Random()
    u = u0.copy()
    if mode == "joint":
        cur = fast.joint_ll(u)
        for _ in range(max_sweeps):
            improved = False
            for a in range(26):
                for b in range(a + 1, 26):
                    u[a], u[b] = u[b], u[a]
                    v = fast.joint_ll(u)
                    if v > cur:
                        cur = v
                        improved = True
                    else:
                        u[a], u[b] = u[b], u[a]
            if not improved:
                break
        return cur, u, None
    else:  # crack objective, warm-starting the substitution each move
        sc, sigma = fast.crack(u, warm)
        for _ in range(max_sweeps):
            improved = False
            for a in range(26):
                for b in range(a + 1, 26):
                    u[a], u[b] = u[b], u[a]
                    ns, nsig = fast.crack(u, sigma, max_sweeps=4)
                    if ns > sc:
                        sc, sigma = ns, nsig
                        improved = True
                    else:
                        u[a], u[b] = u[b], u[a]
            if not improved:
                break
        return sc, u, sigma


def ils(fast: Fast, seconds: float, seed: int, mode="joint", verbose=False):
    rng = random.Random(seed)
    t_end = time.time() + seconds
    u = C.rng_perm(rng)
    best, u, sigma = hc(fast, u, mode, rng=rng)
    best_u, best_sigma = u.copy(), (sigma.copy() if sigma is not None else None)
    rounds = 0
    while time.time() < t_end:
        rounds += 1
        cand = best_u.copy()
        for _ in range(rng.choice([2, 3, 4, 6])):
            a, b = rng.randrange(26), rng.randrange(26)
            cand[a], cand[b] = cand[b], cand[a]
        v, cand, sig = hc(fast, cand, mode, max_sweeps=6, rng=rng,
                          warm=best_sigma)
        if v > best:
            best, best_u = v, cand.copy()
            if sig is not None:
                best_sigma = sig.copy()
            if verbose:
                print(f"    [{seed}] round {rounds}: {best:.1f}")
    return best, best_u, best_sigma, rounds


# ------------------------------------------------------------------- benchmark

def synthetic(ct_len=409, seed=42):
    rng = random.Random(seed)
    src = (C.REPO / "examples" / "english_samples.txt").read_text()
    letters = "".join(ch for ch in src.upper() if "A" <= ch <= "Z")
    pt = letters[0:ct_len]
    top = C.to_text(C.rng_perm(rng))
    bottom = C.to_text(C.rng_perm(rng))
    ct = C.encrypt_text(pt, top, bottom)
    return pt, top, bottom, ct


def gt_u(bottom: str) -> np.ndarray:
    u = np.zeros(26, dtype=np.int64)
    for i, ch in enumerate(bottom):
        u[ord(ch) - 65] = i
    return u


def struct_dist(u, u_true):
    best = 99
    for mirror in (False, True):
        t = (-u_true) % 26 if mirror else u_true
        d = (u - t) % 26
        _, counts = np.unique(d, return_counts=True)
        best = min(best, 26 - counts.max())
    return int(best)


def mode_basin():
    pt, top, bottom, ct = synthetic()
    fast = Fast(ct)
    u_true = gt_u(bottom)
    print(f"ciphertext len {len(ct)}; true crack score {fast.crack(u_true)[0]:.0f}")
    print("perturb-by-k-swaps -> can HC recover the truth?")
    for k in (1, 2, 3, 4, 6, 8, 11, 13):
        hits = 0
        trials = 12
        t0 = time.time()
        for t in range(trials):
            rng = random.Random(1000 * k + t)
            u = u_true.copy()
            for _ in range(k):
                a, b = rng.randrange(26), rng.randrange(26)
                u[a], u[b] = u[b], u[a]
            v, u2, _ = hc(fast, u, "joint", rng=rng)
            if struct_dist(u2, u_true) == 0:
                hits += 1
        print(f"  k={k:2d} swaps: recovered {hits}/{trials}  ({time.time()-t0:.1f}s)")


def mode_bench(seconds: float = 60.0, nproc: int = 2):
    import multiprocessing as mp

    pt, top, bottom, ct = synthetic()
    fast = Fast(ct)
    u_true = gt_u(bottom)
    print(f"true key: top={top} bottom={bottom}")
    print(f"true crack score: {fast.crack(u_true)[0]:.1f}")
    slice_s = seconds / nproc
    with mp.Pool(nproc) as pool:
        res = pool.starmap(_bench_worker, [(ct, slice_s, 100 + i) for i in range(nproc)])
    res.sort(key=lambda r: -r[0])
    print("results (score, structdist to truth, first 70 letters):")
    for sc, sd, txt in res:
        print(f"  {sc:9.1f}  dist={sd:2d}  {txt[:70]}")
    print(f"truth   : {pt[1:71]}")


def _bench_worker(ct, seconds, seed):
    fast = Fast(ct)
    best, u, sig, rounds = ils(fast, seconds, seed, mode="crack")
    txt = fast.text(u, sig)
    return best, struct_dist(u, gt_u_key(ct)), txt


def gt_u_key(ct):
    # recompute truth for this ct (deterministic synthetic)
    pt, top, bottom, _ = synthetic()
    return gt_u(bottom)


def mode_real(seconds: float = 300.0, seed0: int = 7):
    ct = (WORK / "challenge.txt").read_text().strip()
    fast = Fast(ct)
    print(f"ciphertext: {len(ct)} letters")
    best = (-1e18, None, None)
    t0 = time.time()
    rng = random.Random(seed0)
    round_no = 0
    while time.time() - t0 < seconds:
        round_no += 1
        v, u, sig, rounds = ils(fast, min(45.0, seconds - (time.time() - t0)),
                                seed0 + round_no, mode="crack")
        txt = fast.text(u, sig)
        if v > best[0]:
            best = (v, u.copy(), sig.copy(), txt)
            print(f"[{time.time()-t0:6.0f}s] new best {v:.1f}: {txt[:80]}")
    if best[1] is not None:
        top_k = C.to_text(best[2])
        bottom_k = C.to_text(np.argsort(best[1]))
        head = _best_first_letter(fast.dist(best[1]), best[2]) + best[3]
        out = {
            "score": best[0],
            "top": top_k,
            "bottom": bottom_k,
            "plaintext_letters": head,
            "note": "first plaintext letter unrecoverable from ciphertext alone",
        }
        (WORK / "solution.json").write_text(json.dumps(out, indent=2))
        print("saved solution.json")


def _best_first_letter(d, sigma):
    cur = sigma[d]
    best, letter = -1e18, "?"
    for x in range(26):
        seq = np.concatenate(([x], cur))
        sc = C.qg_score(seq)
        if sc > best:
            best, letter = sc, chr(65 + x)
    return letter


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["basin", "bench", "real"])
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    if a.mode == "basin":
        mode_basin()
    elif a.mode == "bench":
        mode_bench(a.seconds)
    else:
        mode_real(a.seconds, a.seed)


if __name__ == "__main__":
    main()
