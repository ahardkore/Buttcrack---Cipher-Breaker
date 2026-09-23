#!/usr/bin/env python3
"""Calibrate the plaintext scoring constants against measured data.

``buttcrack.lang`` turns three raw statistics into a single 0..1 confidence with
linear ramps.  Where those ramps start and end should not be guessed, so this
script measures them:

* reads English samples from ``examples/english_samples.txt``;
* scores the true plaintexts (the "good" distribution);
* scores a set of deliberate failures -- random letters, wrong Caesar shifts,
  reversed text, near-miss substitution keys, transposed text (the "bad"
  distribution);
* prints percentiles and the constants it recommends.

Run it after changing the language model or the scoring maths::

    python3 scripts/calibrate_scoring.py
"""

from __future__ import annotations

import argparse
import random
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from buttcrack.lang import LanguageModel  # noqa: E402
from buttcrack.text import A26, letters_only  # noqa: E402


def load_samples(path: Path) -> list[str]:
    text = path.read_text()
    samples = [letters_only(s) for s in text.split("\n") if s.strip()]
    # The file is prose paragraphs; merge into a handful of long samples and
    # also keep some short ones, because short texts score worse and the
    # calibration has to cover both.
    joined = "".join(samples)
    out = []
    for size in (120, 250, 500, 1000):
        for start in range(0, min(len(joined), size * 6), size):
            chunk = joined[start : start + size]
            if len(chunk) >= size * 0.9:
                out.append(chunk)
    return out


def caesar(text: str, shift: int) -> str:
    return "".join(A26[(A26.index(c) + shift) % 26] for c in text)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--samples", type=Path, default=REPO_ROOT / "examples" / "english_samples.txt")
    ap.add_argument("--seed", type=int, default=1234)
    args = ap.parse_args(argv)

    rng = random.Random(args.seed)
    model = LanguageModel.get()
    samples = load_samples(args.samples)
    print(f"{len(samples)} English samples, {min(map(len, samples))}-{max(map(len, samples))} letters\n")

    # Three classes, because "failure" is not one thing:
    #   english -- true plaintext; the confidence ramp must reach ~1 here.
    #   noise   -- genuinely wrong output (random letters, wrong Caesar shift,
    #              reversed, shuffled).  The ramp must be ~0 here.
    #   nearmiss-- a decryption with a handful of letters still wrong.  It IS
    #              mostly English, so it must score high enough to be surfaced
    #              as a candidate but below the true plaintext.
    stats = lambda: {"fitness": [], "words": [], "segmentation": [], "ic": [], "chi": []}
    good, bad, near = stats(), stats(), stats()

    def record(bucket: dict, text: str) -> None:
        s = model.score(text)
        bucket["fitness"].append(s.fitness)
        bucket["words"].append(s.words)
        bucket["segmentation"].append(s.segmentation)
        bucket["ic"].append(s.ic)
        bucket["chi"].append(s.chi_squared / max(len(text), 1))

    for sample in samples:
        record(good, sample)
        record(bad, "".join(rng.choice(A26) for _ in sample))            # pure noise
        for k in range(1, 26):                                            # wrong Caesar shifts
            record(bad, caesar(sample, k))
        record(bad, sample[::-1])                                         # reversed
        shuffled = list(sample)                                           # shuffled (transposition gone wrong)
        rng.shuffle(shuffled)
        record(bad, "".join(shuffled))
        for swaps in (2, 4, 6, 8):                                        # near-miss substitutions
            key = list(A26)
            rng.shuffle(key)
            for i in rng.sample(range(26), 26 - swaps):
                key[A26.index(A26[i])] = A26[i]
            record(near, "".join(key[A26.index(c)] for c in sample))

    def describe(name: str) -> None:
        g, b, n = good[name], bad[name], near[name]
        print(f"{name:>12}  english min {min(g):8.3f} med {statistics.median(g):8.3f}  |  "
              f"noise max {max(b):8.3f} p95 {sorted(b)[int(len(b)*0.95)]:8.3f} med {statistics.median(b):8.3f}  |  "
              f"nearmiss min {min(n):8.3f} med {statistics.median(n):8.3f}")

    print("Raw statistic distributions")
    print("-" * 132)
    for name in good:
        describe(name)

    print("\nRecommended ramp constants for buttcrack/lang.py")
    print("-" * 118)
    # GOOD = the weakest real English we must still accept;
    # BAD  = the strongest *noise* we must still reject.  Near-misses are
    # deliberately allowed to land in between: they are real partial solutions.
    def percentile(values, q):
        return sorted(values)[min(len(values) - 1, int(len(values) * q))]

    print(f"FITNESS_GOOD = {min(good['fitness']):.2f}   # weakest true English")
    print(f"FITNESS_BAD  = {percentile(bad['fitness'], 0.99):.2f}   # strongest 1% of noise")
    print(f"WORDS_GOOD   = {min(good['words']):.2f}")
    print(f"WORDS_BAD    = {percentile(bad['words'], 0.99):.2f}")
    print(f"SEG_GOOD     = {min(good['segmentation']):.2f}")
    print(f"SEG_BAD      = {percentile(bad['segmentation'], 0.99):.2f}")

    # Sanity: with the recommended constants, how separable are the classes?
    from buttcrack.lang import WEIGHTS, ramp

    fg, fb = min(good["fitness"]), percentile(bad["fitness"], 0.99)
    wg, wb = min(good["words"]), percentile(bad["words"], 0.99)
    sg, sb = min(good["segmentation"]), percentile(bad["segmentation"], 0.99)

    def confidence(fit, cov, seg):
        return (
            WEIGHTS["fitness"] * ramp(fit, fg, fb)
            + WEIGHTS["words"] * ramp(cov, wg, wb)
            + WEIGHTS["segmentation"] * ramp(seg, sg, sb)
        )

    gc = [confidence(good["fitness"][i], good["words"][i], good["segmentation"][i]) for i in range(len(samples))]
    bc = [confidence(bad["fitness"][i], bad["words"][i], bad["segmentation"][i]) for i in range(len(bad["fitness"]))]
    nc = [confidence(near["fitness"][i], near["words"][i], near["segmentation"][i]) for i in range(len(near["fitness"]))]
    print(f"\nSeparation check")
    print(f"  english  confidence: min {min(gc):.3f}  median {statistics.median(gc):.3f}  (want min >= 0.80)")
    print(f"  noise    confidence: max {max(bc):.3f}  median {statistics.median(bc):.3f}  (want max <= 0.30)")
    print(f"  nearmiss confidence: min {min(nc):.3f}  median {statistics.median(nc):.3f}  (want median >= 0.45)")
    overlap = sum(1 for b in bc if b >= min(gc))
    print(f"  noise candidates scoring at or above the weakest english: {overlap}/{len(bc)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
