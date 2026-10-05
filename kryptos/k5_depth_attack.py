#!/usr/bin/env python3
"""K5 DEPTH ATTACK — tooling staged for the day Paradigm releases K5.

Why this is the highest-value thing to build before release
-----------------------------------------------------------
Sanborn confirmed that K5 is 97 characters, written at the same time as K4,
and "shares coded words in identical positions with K4". Paradigm holds the
ciphertext and has said it will be released.

Two ciphertexts under one system is categorically easier than one. If the
keystream is position-dependent and additive -- which is what 35 years of
failed periodic analysis points to -- then it cancels under subtraction:

    C4[i] = P4[i] + K[i]
    C5[i] = P5[i] + K[i]
    C4[i] - C5[i] = P4[i] - P5[i]          <- K is gone, whatever it was

The difference stream D is pure plaintext information. You never need to
recover the key at all. This is the classical two-time-pad / "depth" break,
and it is the single most powerful lever that will ever exist against K4.

Three things fall out immediately
---------------------------------
1. DETECTION. D's index of coincidence is a statistic, and IoC is invariant
   under permutation -- so this test still fires even if a shared
   transposition sits on top of the shared keystream.

2. FREE PLAINTEXT. Sanborn released 24 letters of P4. Wherever P4 is known,
   P5[i] = P4[i] - D[i] is known too. 24 letters of K5 for free, instantly,
   before any cryptanalysis.

3. SHARED WORDS LOCATE THEMSELVES. Sanborn's "shares coded words in identical
   positions" has a sharp consequence: wherever P4 and P5 carry the same
   letter, D[i] = 0. Runs of zeros in D are the shared words, visible without
   decrypting anything.

Run:  python3 kryptos/k5_depth_attack.py --selftest
      python3 kryptos/k5_depth_attack.py --c5 OBKR...   (on release day)
"""

from __future__ import annotations

import argparse
import gzip
import math
from collections import Counter
from pathlib import Path

K4_CT = ("OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSO"
         "TWTQSJQSSEKZZWATJKLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR")

K4_ANCHORS: dict[int, str] = {
    **{22 + i: c for i, c in enumerate("EAST")},
    **{26 + i: c for i, c in enumerate("NORTHEAST")},
    **{64 + i: c for i, c in enumerate("BERLIN")},
    **{70 + i: c for i, c in enumerate("CLOCK")},
}

STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
KRY = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
ALPHABETS = {"standard": STD, "KRYPTOS": KRY}

#: English letter frequencies, used only for the depth detector's null model.
ENGLISH_FREQ = [
    .08167, .01492, .02782, .04253, .12702, .02228, .02015, .06094, .06966,
    .00153, .00772, .04025, .02406, .06749, .07507, .01929, .00095, .05987,
    .06327, .09056, .02758, .00978, .02360, .00150, .01974, .00074,
]

ROOT = Path(__file__).resolve().parent.parent
N = 97


# --------------------------------------------------------------------------
# core
# --------------------------------------------------------------------------

def difference(c4: str, c5: str, alpha: str = STD) -> list[int]:
    """D[i] = C4[i] - C5[i]. Equals P4[i] - P5[i] when the keystream is shared."""
    idx = {c: i for i, c in enumerate(alpha)}
    return [(idx[a] - idx[b]) % 26 for a, b in zip(c4, c5)]


def ioc(values: list[int]) -> float:
    n = len(values)
    counts = Counter(values)
    return sum(v * (v - 1) for v in counts.values()) / (n * (n - 1))


def expected_difference_ioc() -> float:
    """IoC of P4-P5 when both are English: sum_d (sum_a p(a)p(a-d))^2."""
    dist = [sum(ENGLISH_FREQ[a] * ENGLISH_FREQ[(a - d) % 26] for a in range(26))
            for d in range(26)]
    total = sum(dist)
    return sum((x / total) ** 2 for x in dist)


def detect_depth(c4: str, c5: str) -> list[tuple[str, float, float, str]]:
    """Does a shared additive keystream hold? IoC is permutation-invariant,
    so this fires even under a shared transposition."""
    english = expected_difference_ioc()
    random_null = 1 / 26
    rows = []
    for name, alpha in ALPHABETS.items():
        try:
            d = difference(c4, c5, alpha)
        except KeyError:
            continue
        observed = ioc(d)
        margin = (observed - random_null) / (english - random_null)
        verdict = ("DEPTH CONFIRMED" if margin > 0.5 else
                   "possible depth" if margin > 0.25 else "no depth signal")
        rows.append((name, observed, margin, verdict))
    return rows


def propagate_anchors(d: list[int], alpha: str = STD) -> dict[int, str]:
    """P5[i] = P4[i] - D[i] wherever P4 is artist-confirmed. 24 free letters."""
    idx = {c: i for i, c in enumerate(alpha)}
    out = {}
    for pos, letter in K4_ANCHORS.items():
        i = pos - 1
        out[pos] = alpha[(idx[letter] - d[i]) % 26]
    return out


def shared_spans(d: list[int], min_run: int = 3) -> list[tuple[int, int, str]]:
    """Runs of D == 0 are positions where P4 and P5 carry identical letters --
    Sanborn's 'coded words in identical positions', self-locating."""
    spans, start = [], None
    for i, v in enumerate(d + [None]):
        if v == 0 and start is None:
            start = i
        elif v != 0 and start is not None:
            if i - start >= min_run:
                spans.append((start + 1, i, f"{i - start} letters"))
            start = None
    return spans


def load_words(min_len: int = 4, max_len: int = 12) -> list[str]:
    words: set[str] = set()
    wl = ROOT / "kryptos" / "all_words.txt"
    if wl.exists():
        for line in wl.read_text(errors="ignore").split():
            w = line.strip().upper()
            if w.isalpha() and min_len <= len(w) <= max_len:
                words.add(w)
    return sorted(words)


def load_quadgrams() -> tuple[dict[str, float], float]:
    path = ROOT / "buttcrack" / "data" / "english_quadgrams.txt.gz"
    counts: dict[str, int] = {}
    with gzip.open(path, "rt") as fh:
        for line in fh:
            gram, _, num = line.partition(" ")
            if num:
                counts[gram] = int(num)
    total = sum(counts.values())
    return ({g: math.log10(c / total) for g, c in counts.items()},
            math.log10(0.01 / total))


def crib_drag(d: list[int], words: list[str], table, floor, alpha: str = STD,
              top: int = 20, mask: set[int] | None = None) -> list[tuple[float, int, str, str]]:
    """Assume a word sits in P4 at position j; read off the implied P5 fragment
    and score it. A real crib makes English appear on BOTH sides at once.

    Positions inside a D == 0 run are masked out. There, P5 equals P4 by
    definition, so every word trivially "implies" itself and scores as perfect
    English while carrying no information. Those spans are already recovered
    by shared_spans(); dragging over them only produces ties. Excluding them
    is what makes the ranking mean anything.
    """
    idx = {c: i for i, c in enumerate(alpha)}
    mask = mask or set()
    hits: list[tuple[float, int, str, str]] = []
    seen: set[tuple[str, str]] = set()
    for w in words:
        L = len(w)
        if L < 5:
            continue
        wi = [idx[c] for c in w]
        for j in range(N - L + 1):
            if any((j + k) in mask for k in range(L)):
                continue
            other = "".join(alpha[(wi[k] - d[j + k]) % 26] for k in range(L))
            if other == w:
                continue
            key = (w, other)
            if key in seen:
                continue
            seen.add(key)
            sc = sum(table.get(other[k:k + 4], floor) for k in range(L - 3))
            hits.append((sc / (L - 3), j + 1, w, other))
    hits.sort(key=lambda t: -t[0])
    return hits[:top]


def zero_mask(d: list[int], min_run: int = 3) -> set[int]:
    """0-indexed positions lying inside a run of D == 0."""
    out: set[int] = set()
    for start, end, _ in shared_spans(d, min_run):
        out.update(range(start - 1, end))
    return out


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

def selftest() -> int:
    print("K5 DEPTH ATTACK — SELF-TEST ON SYNTHETIC DEPTH")
    print("=" * 78)

    p4 = ("THECOMPASSROSEISHEREXEASTNORTHEASTTHISISYOURPOSITIONX"
          "COMMISSIONBERLINCLOCKWHICHISNORTHEASTOFHEREX")
    # P5 built the way Sanborn described: same length, coded words in
    # identical positions (the shared prefix and the shared POSITION phrase).
    p5 = ("THECOMPASSROSEISHEREXEASTSOUTHEASTTHISISYOURPOSITIONX"
          "ITSBURIEDOUTTHERESOMEWHEREATTHESURVEYMARKERX")
    assert len(p4) == len(p5) == N

    import random
    rng = random.Random(1990)
    keystream = [rng.randrange(26) for _ in range(N)]
    idx = {c: i for i, c in enumerate(STD)}
    c4 = "".join(STD[(idx[p4[i]] + keystream[i]) % 26] for i in range(N))
    c5 = "".join(STD[(idx[p5[i]] + keystream[i]) % 26] for i in range(N))
    print("\nPlanted: two English plaintexts under ONE random 97-symbol keystream.")
    print(f"  synthetic C4  {c4}")
    print(f"  synthetic C5  {c5}")

    ok = True

    print("\n1. Depth detection (keystream never supplied to the detector)")
    for name, observed, margin, verdict in detect_depth(c4, c5):
        print(f"   {name:<10} IoC(D)={observed:.4f}  margin={margin:5.2f}  {verdict}")
    fired = any(m > 0.5 for _, _, m, _ in detect_depth(c4, c5))
    ok &= fired
    print(f"   expected IoC for English-minus-English: {expected_difference_ioc():.4f}"
          f"   random: {1/26:.4f}")
    print(f"   {'PASS' if fired else 'FAIL'}")

    d = difference(c4, c5)

    print("\n2. Anchor propagation: P5 = P4 - D at the 24 confirmed positions")
    got = propagate_anchors(d)
    exact = all(got[pos] == p5[pos - 1] for pos in got)
    ok &= exact
    for label, span in (("EAST", range(22, 26)), ("NORTHEAST", range(26, 35)),
                        ("BERLIN", range(64, 70)), ("CLOCK", range(70, 75))):
        rec = "".join(got[p] for p in span)
        true = "".join(p5[p - 1] for p in span)
        print(f"   P4 {label:<10} -> P5 recovered {rec:<10} actual {true:<10} "
              f"{'ok' if rec == true else 'MISMATCH'}")
    print(f"   {'PASS' if exact else 'FAIL'} — 24 letters of K5 recovered with zero cryptanalysis")

    print("\n3. Shared-word localisation: runs of D == 0")
    spans = shared_spans(d)
    print(f"   found {len(spans)} shared spans >= 3 letters")
    for start, end, size in spans:
        print(f"     positions {start:>3}-{end:<3} ({size})  P4/P5 agree: "
              f"{p4[start-1:end]!r}")
    truth = [(s, e) for s, e, _ in spans if p4[s - 1:e] == p5[s - 1:e]]
    allgood = len(truth) == len(spans) and len(spans) > 0
    ok &= allgood
    print(f"   {'PASS' if allgood else 'FAIL'} — every detected span is genuinely shared")

    print("\n4. Mutual crib drag (top hits should be real words at real positions)")
    table, floor = load_quadgrams()
    words = [w for w in load_words(5, 10)][:40000]
    mask = zero_mask(d)
    print(f"   masking {len(mask)} positions inside D==0 runs (already recovered above)")
    hits = crib_drag(d, words, table, floor, top=8, mask=mask)
    for sc, pos, w, other in hits:
        truth = "<-- correct" if p4[pos - 1:pos - 1 + len(w)] == w else ""
        print(f"   {sc:7.2f}  pos {pos:>3}  P4={w:<12} implies P5={other:<12} {truth}")
    found = any(p4[pos - 1:pos - 1 + len(w)] == w for _, pos, w, _ in hits)
    ok &= found
    print(f"   {'PASS' if found else 'FAIL'} — a genuine crib surfaced in the top hits")

    print("\n" + "=" * 78)
    print("SELF-TEST PASSED — ready for K5." if ok else "SELF-TEST FAILED.")
    return 0 if ok else 1


def run_live(c5: str) -> int:
    c5 = "".join(ch for ch in c5.upper() if ch.isalpha())
    print("K5 DEPTH ATTACK — LIVE")
    print("=" * 78)
    if len(c5) != N:
        print(f"K5 must be {N} letters; got {len(c5)}.")
        return 2
    print(f"  K4  {K4_CT}")
    print(f"  K5  {c5}")

    print("\n1. Depth detection")
    rows = detect_depth(K4_CT, c5)
    for name, observed, margin, verdict in rows:
        print(f"   {name:<10} IoC(D)={observed:.4f}  margin={margin:5.2f}  {verdict}")
    best = max(rows, key=lambda r: r[2])
    if best[2] <= 0.25:
        print("\n   No shared-keystream signal. The two panels do not sit in depth")
        print("   under a common additive keystream. Fall back to independent attack.")
        return 1

    alpha = ALPHABETS[best[0]]
    d = difference(K4_CT, c5, alpha)

    print(f"\n2. Free plaintext for K5 (alphabet: {best[0]})")
    for pos, letter in sorted(propagate_anchors(d, alpha).items()):
        print(f"   pos {pos:>3}  K4={K4_ANCHORS[pos]}  ->  K5={letter}")

    print("\n3. Shared spans (D == 0)")
    for start, end, size in shared_spans(d):
        print(f"   positions {start:>3}-{end:<3} ({size}) — identical letters in both")

    print("\n4. Mutual crib drag")
    table, floor = load_quadgrams()
    mask = zero_mask(d)
    print(f"   masking {len(mask)} positions inside D==0 runs")
    for sc, pos, w, other in crib_drag(d, load_words(5, 10), table, floor, alpha,
                                       top=25, mask=mask):
        print(f"   {sc:7.2f}  pos {pos:>3}  K4={w:<12} implies K5={other}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--c5", type=str, help="the K5 ciphertext, once released")
    args = ap.parse_args()
    if args.c5:
        return run_live(args.c5)
    return selftest()


if __name__ == "__main__":
    raise SystemExit(main())
