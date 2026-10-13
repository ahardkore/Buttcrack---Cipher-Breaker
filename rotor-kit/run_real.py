#!/usr/bin/env python3
"""Portfolio search: fast SA on the necklace (fixed-substitution kernel) with
periodic exact re-cracking, running on synthetic (validation) and the real
challenge ciphertext simultaneously."""
import json, math, os, random, sys, time
import numpy as np
import common as C
import solver2 as S

def uni_sigma(d):
    dist = np.bincount(d, minlength=26).astype(np.float64)
    order = np.argsort(-dist, kind="stable")
    qorder = np.argsort(-C.ENGLISH_FREQ_PCT, kind="stable")
    s = np.empty(26, dtype=np.int64); s[order] = qorder
    return s

def obj_kernel(u, c0, c1, sigma):
    d = (u[c1] - u[c0]) % 26
    t = sigma[d]
    return float(C.LOG_BI_MAT[t[:-1], t[1:]].sum())

def sa(fast, u, sigma, seconds, rng, T0=6.0, T1=0.05):
    c0, c1 = fast.c0, fast.c1
    u = u.copy()
    cur = obj_kernel(u, c0, c1, sigma)
    best, bestu = cur, u.copy()
    t_end = time.time() + seconds
    t_start = time.time()
    while True:
        now = time.time()
        if now >= t_end:
            break
        frac = (now - t_start) / seconds
        T = T0 * (T1 / T0) ** frac
        a, b = rng.randrange(26), rng.randrange(26)
        if a == b:
            continue
        u[a], u[b] = u[b], u[a]
        v = obj_kernel(u, c0, c1, sigma)
        if v >= cur or rng.random() < math.exp(min(0.0, (v - cur) / T)):
            cur = v
            if v > best:
                best, bestu = v, u.copy()
        else:
            u[a], u[b] = u[b], u[a]
    return best, bestu

def worker(which, seconds, seed, outpath):
    rng = random.Random(seed)
    if which == "synthetic":
        pt, top, bottom, ct = S.synthetic()
        u_true = S.gt_u(bottom)
    else:
        ct = open(os.path.join(os.path.dirname(__file__), "challenge.txt")).read().strip()
        u_true = None
    fast = S.Fast(ct)
    best = (-1e18, None, None)
    sigma = None
    rounds = 0
    t0 = time.time()
    log = open(outpath, "w")
    while time.time() - t0 < seconds:
        rounds += 1
        u0 = C.rng_perm(rng)
        if sigma is None:
            sigma = uni_sigma(fast.dist(u0))
        # SA phase (fast)
        _, u1 = sa(fast, u0, sigma, seconds=6.0, rng=rng)
        if best[1] is not None and rng.random() < 0.5:
            # intensify around the incumbent: start SA from best with few swaps
            ub = best[1].copy()
            for _ in range(rng.randrange(1, 4)):
                a, b = rng.randrange(26), rng.randrange(26)
                ub[a], ub[b] = ub[b], ub[a]
            k_, ub2 = sa(fast, ub, best[2], seconds=6.0, rng=rng)
            if k_ > -1e17:
                u1 = ub2
        # exact crack phase
        sc, sig = fast.crack(u1, best[2] if best[2] is not None else None, max_sweeps=16)
        if sc > best[0]:
            best = (sc, u1.copy(), sig.copy())
            txt = fast.text(u1, sig)
            rec = {"round": rounds, "t": round(time.time() - t0, 1), "score": sc,
                   "text": txt, "u": [int(x) for x in u1]}
            if u_true is not None:
                rec["struct_dist"] = S.struct_dist(u1, u_true)
                rec["solved"] = rec["struct_dist"] == 0
            log.write(json.dumps(rec) + "\n"); log.flush()
            print(f"[{which} {time.time()-t0:6.0f}s r{rounds}] {sc:8.1f} "
                  f"{'SOLVED ' if rec.get('solved') else ''}{txt[:60]}", flush=True)
        sigma = sig
    log.close()
    return best

if __name__ == "__main__":
    which = sys.argv[1]
    seconds = float(sys.argv[2])
    seed = int(sys.argv[3])
    out = sys.argv[4]
    r = worker(which, seconds, seed, out)
    print(f"{which}: final {r[0]:.1f}")
