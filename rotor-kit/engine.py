#!/usr/bin/env python3
"""Alternating (necklace, substitution) search engine, validated on the
synthetic 409-letter instance, then run on the challenge ciphertext."""
from __future__ import annotations

import json, math, os, random, sys, time
import numpy as np
import common as C
import solver2 as S


class Fast2(S.Fast):
    """S.Fast plus the plain fixed-substitution score used by the fast steps."""

    def score(self, u, sigma):
        t = sigma[self.dist(u)]
        return C.qg_score(t)


def uni_sigma(d):
    dist = np.bincount(d, minlength=26).astype(np.float64)
    order = np.argsort(-dist, kind="stable")
    qorder = np.argsort(-C.ENGLISH_FREQ_PCT, kind="stable")
    s = np.empty(26, dtype=np.int64)
    s[order] = qorder
    return s


def u_step(fast: Fast2, u, sigma, cur, rng, sweeps=3):
    pairs = [(a, b) for a in range(26) for b in range(a + 1, 26)]
    for _ in range(sweeps):
        rng.shuffle(pairs)
        improved = False
        for a, b in pairs:
            u[a], u[b] = u[b], u[a]
            v = fast.score(u, sigma)
            if v > cur:
                cur = v
                improved = True
            else:
                u[a], u[b] = u[b], u[a]
        if not improved:
            break
    return cur


def cycle(fast: Fast2, u, sigma, rng, u_sweeps=3, s_sweeps=6):
    cur = fast.score(u, sigma)
    cur = u_step(fast, u, sigma, cur, rng, u_sweeps)
    sc, sigma = fast.crack(u, sigma, max_sweeps=s_sweeps)
    return u, sigma, sc


def sa_u(fast: Fast2, u, sigma, seconds, rng, T0=8.0, T1=0.05):
    u = u.copy()
    cur = fast.score(u, sigma)
    best, bestu = cur, u.copy()
    t0 = time.time()
    while True:
        now = time.time()
        if now - t0 >= seconds:
            break
        T = T0 * (T1 / T0) ** ((now - t0) / seconds)
        a, b = rng.randrange(26), rng.randrange(26)
        if a == b:
            continue
        u[a], u[b] = u[b], u[a]
        v = fast.score(u, sigma)
        if v >= cur or rng.random() < math.exp(min(0.0, (v - cur) / T)):
            cur = v
            if v > best:
                best, bestu = v, u.copy()
        else:
            u[a], u[b] = u[b], u[a]
    return best, bestu


def worker(which, seconds, seed, logpath):
    rng = random.Random(seed)
    if which == "synthetic":
        pt, top, bottom, ct = S.synthetic()
        u_true = S.gt_u(bottom)
    else:
        ct = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "challenge.txt")).read().strip()
        u_true = None
    fast = Fast2(ct)
    log = open(logpath, "w")
    best = (-1e18, None, None)
    cur_u = C.rng_perm(rng)
    sigma = uni_sigma(fast.dist(cur_u))
    cur_u, sigma, sc = cycle(fast, cur_u, sigma, rng)
    best = (sc, cur_u.copy(), sigma.copy())
    t0 = time.time()
    rounds = 0
    while time.time() - t0 < seconds:
        rounds += 1
        # SA burst at fixed sigma (fast travel), then re-crack
        v, u2 = sa_u(fast, best[1], best[2], seconds=2.5, rng=rng)
        u2, sigma2, sc2 = cycle(fast, u2, best[2], rng)
        if sc2 > best[0]:
            best = (sc2, u2.copy(), sigma2.copy())
            txt = fast.text(u2, sigma2)
            rec = {"round": rounds, "t": round(time.time() - t0, 1),
                   "score": sc2, "text": txt, "u": [int(x) for x in u2]}
            if u_true is not None:
                rec["struct_dist"] = S.struct_dist(u2, u_true)
                rec["solved"] = rec["struct_dist"] == 0
                if rec["solved"]:
                    rec["key_top"] = C.to_text(sigma2)
                    rec["key_bottom"] = C.to_text(np.argsort(u2))
            log.write(json.dumps(rec) + "\n")
            log.flush()
            print(f"[{which} {time.time()-t0:6.0f}s r{rounds}] {sc2:8.1f} "
                  f"{'*** SOLVED *** ' if rec.get('solved') else ''}{txt[:64]}", flush=True)
        else:
            # drift: keep a perturbed incumbent as the new search point
            pass
    log.close()
    return best


if __name__ == "__main__":
    worker(sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
