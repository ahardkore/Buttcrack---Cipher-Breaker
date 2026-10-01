#!/usr/bin/env python3
"""Re-measure the numbers the README quotes.

Every performance claim in the README should be reproducible by someone who
clones the repository, and the ones that are not get quietly stale. This
script re-runs the measurable ones and prints what it got, so the docs can be
corrected against the output rather than against memory.

    python3 scripts/bench_claims.py --all
    python3 scripts/bench_claims.py --gate --cribs       # the quick ones

Timings depend on the machine; what should not vary is the shape of the
result (what solves, what does not, how many of N).
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from buttcrack.ciphers import get  # noqa: E402
from buttcrack.ciphers.base import CrackContext  # noqa: E402
from buttcrack.lang import get_model  # noqa: E402
from buttcrack.text import A26, letters_only  # noqa: E402

CORPUS = ROOT / "examples" / "english_samples.txt"
MODEL = get_model()


def sample(rng: random.Random, n: int) -> str:
    text = letters_only(CORPUS.read_text()).upper()
    start = rng.randrange(0, max(1, len(text) - n - 1))
    return text[start : start + n]


def gate() -> None:
    """Chi-squared per letter, best of the rotations: the transposition gate."""
    MODEL.load()
    text = letters_only(CORPUS.read_text()).upper()[:4000]

    def statistic(t: str) -> float:
        s = letters_only(t).upper()
        return min(
            MODEL.chi_squared("".join(A26[(A26.index(c) - r) % 26] for c in s), per_char=True)
            for r in range(26)
        )

    stack = get("rot13").encrypt(
        get("rail_fence").encrypt(
            get("skip").encrypt(get("reverse").encrypt(text), 5), 4
        )
    )
    rows = [
        ("English", text),
        ("rail fence", get("rail_fence").encrypt(text, 4)),
        ("columnar", get("columnar").encrypt(text, "SPIES")),
        ("Myszkowski", get("myszkowski").encrypt(text, "TOMATO")),
        ("AMSCO", get("amsco").encrypt(text, "ZEBRA")),
        ("four-cipher stack", stack),
        ("Vigenere", get("vigenere").encrypt(text, "LANTERN")),
        ("Hill 2x2", get("hill").encrypt(text, "HILL")),
        ("substitution", get("substitution").encrypt(text, "QWERTYUIOPASDFGHJKLZXCVBNM")),
    ]
    print("\nTransposition gate (chi-squared per letter, best of 26 rotations)")
    print(f"  corpus: {CORPUS.relative_to(ROOT)}, first 4000 letters")
    for name, t in rows:
        print(f"    {name:20} {statistic(t):.3f}")


def cribs(trials: int = 5, budget: float = 25.0) -> None:
    """Sum-clock recovery against crib length, four wheels of 4, 5, 6, 7."""
    MODEL.load()
    sc = get("sum_clock")
    print(f"\nSum-clock, wheels 4/5/6/7, 153 letters, {trials} trials, {budget:.0f}s budget")
    for crib_len in (12, 14, 16, 19):
        rng = random.Random(11)
        solved, times = 0, []
        for _ in range(trials):
            pt = sample(rng, 153)
            wheels = [[rng.randrange(26) for _ in range(p)] for p in (4, 5, 6, 7)]
            ct = sc.encrypt(pt, {"periods": [4, 5, 6, 7], "wheels": wheels, "alphabet": "kryptos"})
            ctx = CrackContext.create(model=MODEL, budget=budget, hints={"crib": pt[:crib_len]})
            started = time.time()
            found = list(sc.crack(ct, ctx))
            times.append(time.time() - started)
            solved += bool(found) and found[0].plaintext.startswith(pt[:60])
        print(
            f"    crib {crib_len:2} letters: {solved} of {trials}"
            f"   median {sorted(times)[len(times) // 2]:.2f}s"
        )


def m94(trials: int = 6, letters: int = 250, budget: float = 20.0) -> None:
    MODEL.load()
    cipher = get("m94")
    rng = random.Random(3)
    solved, times = 0, []
    for _ in range(trials):
        pt = sample(rng, letters)
        order = list("BCDEFGHIJKLMNOPQRSTUVWXYZ")
        rng.shuffle(order)
        ct = cipher.encrypt(pt, {"order": "".join(order), "row": rng.randrange(1, 25)})
        ctx = CrackContext.create(model=MODEL, budget=budget, workers=2)
        started = time.time()
        found = list(cipher.crack(ct, ctx))
        times.append(time.time() - started)
        solved += bool(found) and found[0].plaintext.startswith(pt[:40])
    print(f"\nM-94, {letters} letters, {budget:.0f}s, 2 workers: {solved} of {trials}")
    print(f"    times {[round(t, 1) for t in times]}")


def kryptos(budget: float = 60.0) -> None:
    import json

    print(f"\nParadigm Kryptos, no hints, {budget:.0f}s budget each")
    from buttcrack import solve

    ciphertexts = json.loads((ROOT / "kryptos" / "pk_all_ciphertexts.json").read_text())
    solutions = json.loads((ROOT / "kryptos" / "pk_verified_solutions.json").read_text())
    for name in (f"PK{i}" for i in range(1, 8)):
        truth = solutions.get(name, {}).get("plaintext", "")
        started = time.time()
        report = solve(ciphertexts[name], budget=budget, workers=2)
        elapsed = time.time() - started
        got = "".join(c for c in report.plaintext.upper() if c.isalpha())
        ok = bool(truth) and got.startswith(truth[:60])
        print(f"    {name}: {'solved' if ok else 'missed ':6} {elapsed:5.1f}s  via {report.path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", action="store_true")
    parser.add_argument("--cribs", action="store_true")
    parser.add_argument("--m94", action="store_true")
    parser.add_argument("--kryptos", action="store_true")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    if not any((args.gate, args.cribs, args.m94, args.kryptos, args.all)):
        parser.print_help()
        return 1
    if args.all or args.gate:
        gate()
    if args.all or args.cribs:
        cribs()
    if args.all or args.m94:
        m94()
    if args.all or args.kryptos:
        kryptos()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
