#!/usr/bin/env python3
"""Measure the score an attack reaches on text that has no answer.

A short ciphertext will hand you an English-looking reading for free if the
key you are fitting has enough freedom in it. The only way to know whether a
"record score" means anything is to run the same attack, at the same effort,
on text with the same letters and no structure at all -- a shuffle. Whatever
the shuffles reach is the floor; a result at or below it is the search
describing itself rather than the cipher.

    python3 scripts/null_floor.py --cipher sum_clock --pk PK9 --budget 120
    python3 scripts/null_floor.py --cipher hill --file ct.txt --trials 6

This exists because PK9's stored "record" of -5.2493 was treated as progress
for a long time. At matched effort the shuffles of PK9 reach the same band,
so the number was never evidence. See kryptos/PK8-PK10.md.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from buttcrack.ciphers import get  # noqa: E402
from buttcrack.ciphers.base import CrackContext  # noqa: E402
from buttcrack.lang import get_model  # noqa: E402
from buttcrack.text import letters_only  # noqa: E402


def best_score(cipher, text: str, model, budget: float, workers: int, exhaustive: bool):
    ctx = CrackContext.create(
        model=model, budget=budget, workers=workers, exhaustive=exhaustive
    )
    started = time.time()
    candidates = list(cipher.crack(text, ctx))
    fitness = max((c.fitness for c in candidates), default=float("-inf"))
    confidence = max((c.confidence for c in candidates), default=0.0)
    return fitness, confidence, time.time() - started


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cipher", required=True, help="registry name, e.g. sum_clock")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--pk", help="challenge id from kryptos/pk_all_ciphertexts.json")
    source.add_argument("--file", help="file holding the ciphertext")
    source.add_argument("--text", help="the ciphertext itself")
    parser.add_argument("--budget", type=float, default=120.0)
    parser.add_argument("--trials", type=int, default=4, help="how many shuffles")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--exhaustive", action="store_true", default=True)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()

    if args.pk:
        text = json.loads((ROOT / "kryptos" / "pk_all_ciphertexts.json").read_text())[args.pk]
    elif args.file:
        text = Path(args.file).read_text().strip()
    else:
        text = args.text
    text = letters_only(text).upper()

    cipher = get(args.cipher)
    model = get_model()
    model.load()

    real, confidence, elapsed = best_score(
        cipher, text, model, args.budget, args.workers, args.exhaustive
    )
    print(f"{args.cipher} on {len(text)} letters, {args.budget:.0f}s per run")
    print(f"  real      fitness {real:7.2f}   confidence {confidence:.3f}   ({elapsed:.0f}s)")

    rng = random.Random(args.seed)
    letters = list(text)
    nulls = []
    for i in range(args.trials):
        rng.shuffle(letters)
        score, conf, _ = best_score(
            cipher, "".join(letters), model, args.budget, args.workers, args.exhaustive
        )
        nulls.append(score)
        print(f"  shuffle {i + 1} fitness {score:7.2f}   confidence {conf:.3f}")

    if not nulls:
        return 0
    mean = statistics.fmean(nulls)
    print(f"\n  null mean {mean:.2f}, null best {max(nulls):.2f}")
    if real > max(nulls):
        margin = real - max(nulls)
        print(f"  VERDICT: real beats every shuffle by {margin:.2f} -- worth following up")
    else:
        print("  VERDICT: real sits inside the null distribution -- this attack, at this")
        print("           effort, explains nothing about this ciphertext")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
