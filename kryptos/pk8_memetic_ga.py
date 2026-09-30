#!/usr/bin/env python3
"""Memetic (genetic + local ascent) attack on PK8-shaped sum-clocks.

Why this exists: the basin probe (kryptos/pk8_basin_probe.py) shows the true
wheels are a strong attractor only within ~3 corrupted coordinates of 22.
Blind annealing and greedy ascent never get that close from a random start.
Recombination is the standard answer to narrow basins: two parents that each
have half the coordinates right can produce a child inside the basin, where
coordinate ascent finishes the job.

Calibration protocol (the honesty bit):
  1. ``--synthetic K`` runs K synthetic instances with known answers and
     reports the recovery rate at the chosen budget.
  2. Only a budget that recovers synthetics is meaningful on the real PK8
     (``--real``).  A failure there then refutes the wheel-set hypothesis
     itself, not the search.

Wheels are gauge-fixed (q4[0] = 0) so crossover doesn't fight the gauge
freedom of the sum.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from buttcrack.ciphers.base import CrackContext  # noqa: E402
from buttcrack.ciphers.keyed import KRYPTOS_ALPHABET, SumClock  # noqa: E402
from buttcrack.lang import get_model  # noqa: E402
from kryptos.pk8_calibrated_recovery import N, PERIODS, decrypt, encrypt, english_pool  # noqa: E402

SLOTS = sum(PERIODS)  # 22 dial positions, one of them gauge


def genome_of(wheels: list[list[int]]) -> tuple[int, ...]:
    g = [v for wheel in wheels for v in wheel]
    gauge = g[0]
    return tuple((v - gauge) % 26 for v in g)


def wheels_of(genome: tuple[int, ...]) -> list[list[int]]:
    out, i = [], 0
    for p in PERIODS:
        out.append(list(genome[i : i + p]))
        i += p
    return out


class Pop:
    def __init__(self, sc: SumClock, ctx: CrackContext, ct: str, rng: random.Random,
                 size: int, p_ascent: float, mut: float):
        self.sc, self.ctx, self.ct, self.rng = sc, ctx, ct, rng
        self.size, self.p_ascent, self.mut = size, p_ascent, mut
        self.model = ctx.model
        self.pool: list[tuple[float, tuple[int, ...]]] = []  # (fit, genome), sorted desc
        self.best_fit, self.best_genome = -1e9, self.random_genome()

    def random_genome(self) -> tuple[int, ...]:
        return (0,) + tuple(self.rng.randrange(26) for _ in range(SLOTS - 1))

    def fitness(self, genome: tuple[int, ...]) -> float:
        return self.model.search_fitness(decrypt(self.ct, wheels_of(genome)))

    def ascend(self, genome: tuple[int, ...]) -> tuple[float, tuple[int, ...]]:
        wheels, fit = self.sc._ascend(self.ct, KRYPTOS_ALPHABET, PERIODS, self.ctx,
                                      self.rng, wheels=wheels_of(genome))
        return fit, genome_of(wheels)

    def note(self, fit: float, genome: tuple[int, ...]) -> None:
        if fit > self.best_fit:
            self.best_fit, self.best_genome = fit, genome

    def run(self, generations: int) -> tuple[float, tuple[int, ...]]:
        # seed population (ascended: start at local optima, GA recombines optima)
        for _ in range(self.size):
            g = self.random_genome()
            f, g = self.ascend(g)
            self.pool.append((f, g))
            self.note(f, g)
        self.pool.sort(key=lambda x: -x[0])
        self.pool = self.pool[: self.size]

        for _gen in range(generations):
            if self.ctx.expired():
                break
            children: list[tuple[float, tuple[int, ...]]] = []
            while len(children) < self.size:
                a = self.pick()
                b = self.pick()
                cut = [self.rng.random() < 0.5 for _ in range(SLOTS)]
                child = tuple(a[i] if cut[i] else b[i] for i in range(SLOTS))
                child = (0,) + tuple((v if self.rng.random() > self.mut else self.rng.randrange(26))
                                     for v in child[1:])
                if self.rng.random() < self.p_ascent:
                    f, child = self.ascend(child)
                else:
                    f = self.fitness(child)
                children.append((f, child))
                self.note(f, child)
            # elitist survival: parents + children, keep best `size` distinct genomes
            seen = {}
            for f, g in sorted(self.pool + children, key=lambda x: -x[0]):
                if g not in seen:
                    seen[g] = f
                if len(seen) >= self.size:
                    break
            self.pool = sorted(((f, g) for g, f in seen.items()), key=lambda x: -x[0])
        return self.best_fit, self.best_genome

    def pick(self) -> tuple[int, ...]:
        i = min(self.rng.randrange(self.size), self.rng.randrange(self.size))  # bias to front
        return self.pool[i][1]


def attack(ct: str, *, budget_s: float, size: int, generations: int, p_ascent: float,
           mut: float, seed: int) -> tuple[float, str]:
    model = get_model()
    sc = SumClock()
    ctx = CrackContext.create(model=model, budget=budget_s)
    rng = random.Random(seed)
    pop = Pop(sc, ctx, ct, rng, size, p_ascent, mut)
    fit, genome = pop.run(generations)
    return fit, decrypt(ct, wheels_of(genome))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--synthetic", type=int, default=0, help="run K calibration instances")
    ap.add_argument("--real", action="store_true", help="attack the real PK8")
    ap.add_argument("--budget", type=float, default=600.0, help="seconds per instance")
    ap.add_argument("--size", type=int, default=80)
    ap.add_argument("--generations", type=int, default=200)
    ap.add_argument("--p-ascent", type=float, default=0.25)
    ap.add_argument("--mut", type=float, default=0.06)
    args = ap.parse_args()

    if args.synthetic:
        rng = random.Random(99)
        pool = english_pool()
        solved = 0
        for k in range(args.synthetic):
            plain = pool[rng.randrange(len(pool))]
            wheels = [[rng.randrange(26) for _ in range(p)] for p in PERIODS]
            ct = encrypt(plain, wheels)
            t0 = time.time()
            fit, pt = attack(ct, budget_s=args.budget, size=args.size,
                             generations=args.generations, p_ascent=args.p_ascent,
                             mut=args.mut, seed=rng.randrange(2**31))
            acc = sum(a == b for a, b in zip(pt, plain)) / len(plain)
            ok = acc >= 0.99
            solved += ok
            print(f"synthetic {k}: fit={fit:.4f} acc={acc * 100:.1f}% solved={ok} "
                  f"({time.time() - t0:.0f}s)", flush=True)
            if ok or k == 0:
                print(f"  truth: {plain[:66]}\n  found: {pt[:66]}", flush=True)
        print(f"CALIBRATION RECOVERY: {solved}/{args.synthetic}")

    if args.real:
        ct = json.loads((ROOT / "kryptos/pk_all_ciphertexts.json").read_text())["PK8"]
        fit, pt = attack(ct, budget_s=args.budget, size=args.size,
                         generations=args.generations, p_ascent=args.p_ascent,
                         mut=args.mut, seed=2026)
        print(f"REAL PK8: fit={fit:.4f}")
        print(pt)


if __name__ == "__main__":
    main()
