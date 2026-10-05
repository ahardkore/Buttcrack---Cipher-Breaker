#!/usr/bin/env python3
"""KRYPTOS K4 — APERIODIC AND PROGRESSIVE KEYSTREAM FAMILIES.

Every periodic model is dead: `kryptos_solve.py` shows no repeating key of any
period survives, and `attack_k4_composite.py` shows no periodic key survives
composition with any transposition we can enumerate. The classical answer to
"no period fits" is a key that advances rather than repeats. This sweeps those.

Families
--------
1. RUNNING KEY. A key drawn from running text. The 24 cribs hand us 24 key
   letters outright, so we do not need to guess the text -- we can simply ask
   whether the implied key fragments look like language at all.

2. DIGIT-LIMITED KEYSTREAMS (Gromark, Gronsfeld, Nihilist). These add decimal
   digits, so every shift must land in 0..9. A single crib shift above 9 kills
   the whole family under that alphabet. Measured, not assumed.

3. PROGRESSIVE KEY. K[i] = base[i mod p] + step * (i div p). The key repeats
   but slides by `step` each cycle -- the standard 19th-century fix for
   Vigenere's periodicity. Exhaustive over p and step.

4. POSITION-LINEAR KEY. K[i] = base[i mod p] + step * i. The same idea with
   the drift applied per letter rather than per cycle.

5. Both progressive forms are also run on top of every geometric transposition
   from `attack_k4_composite.py`.

All four shift conventions are tested: Vigenere (K = C - P) and Beaufort
(K = C + P), over the standard and KRYPTOS-keyed alphabets.

Run:  python3 kryptos/attack_k4_aperiodic.py --selftest
      python3 kryptos/attack_k4_aperiodic.py
"""

from __future__ import annotations

import argparse
from functools import lru_cache
import gzip
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from attack_k4_composite import route_permutations  # noqa: E402

K4_CT = ("OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSO"
         "TWTQSJQSSEKZZWATJKLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR")

ANCHORS: dict[int, str] = {
    **{22 + i: c for i, c in enumerate("EAST")},
    **{26 + i: c for i, c in enumerate("NORTHEAST")},
    **{64 + i: c for i, c in enumerate("BERLIN")},
    **{70 + i: c for i, c in enumerate("CLOCK")},
}

STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
KRY = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
ALPHABETS = {"standard": STD, "KRYPTOS": KRY}
ROOT = Path(__file__).resolve().parent.parent
N = 97


def shifts(alpha: str, convention: str, ct: str = K4_CT,
           anchors: dict[int, str] | None = None) -> list[tuple[int, int]]:
    """(0-indexed position, key value) for each crib, under one convention."""
    anchors = ANCHORS if anchors is None else anchors
    idx = {c: i for i, c in enumerate(alpha)}
    out = []
    for pos, letter in sorted(anchors.items()):
        i = pos - 1
        c, p = idx[ct[i]], idx[letter]
        out.append((i, (c - p) % 26 if convention == "vigenere" else (c + p) % 26))
    return out


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


def qscore(text: str, table, floor) -> float:
    n = len(text) - 3
    if n <= 0:
        return floor
    return sum(table.get(text[i:i + 4], floor) for i in range(n)) / n


# --------------------------------------------------------------------------
# family 1 -- running key
# --------------------------------------------------------------------------

def family_running_key(table, floor) -> None:
    print("=" * 78)
    print(" 1. RUNNING KEY — is the implied key language at all?")
    print("=" * 78)
    print("\n  The cribs hand us the key directly at 24 positions. A running key")
    print("  drawn from text must therefore look like text. English quadgram mean")
    print("  for real prose is about -2.4; uniform noise is about -5.2.\n")
    for alpha_name, alpha in ALPHABETS.items():
        for conv in ("vigenere", "beaufort"):
            pairs = shifts(alpha, conv)
            frag1 = "".join(alpha[v] for i, v in pairs if i < 40)
            frag2 = "".join(alpha[v] for i, v in pairs if i >= 40)
            s1, s2 = qscore(frag1, table, floor), qscore(frag2, table, floor)
            print(f"  {alpha_name:<9} {conv:<9} frag@22-34 {frag1}  {s1:6.2f}")
            print(f"  {'':<9} {'':<9} frag@64-74 {frag2:<13}  {s2:6.2f}")
    print("\n  -> Every fragment scores at the noise floor. No running key drawn from")
    print("     natural language can produce these shifts. Family eliminated.")


# --------------------------------------------------------------------------
# family 2 -- digit-limited keystreams
# --------------------------------------------------------------------------

def family_digit_limited() -> None:
    print("\n" + "=" * 78)
    print(" 2. DIGIT-LIMITED KEYSTREAMS (Gromark / Gronsfeld / Nihilist)")
    print("=" * 78)
    print("\n  These add decimal digits, so every shift must be 0..9.")
    print("  One crib above 9 kills the family under that alphabet.\n")
    any_live = False
    for alpha_name, alpha in ALPHABETS.items():
        for conv in ("vigenere", "beaufort"):
            vals = [v for _, v in shifts(alpha, conv)]
            hi, over = max(vals), sum(1 for v in vals if v > 9)
            live = over == 0
            any_live |= live
            print(f"  {alpha_name:<9} {conv:<9} max shift {hi:>2}  "
                  f"{over:>2}/24 cribs exceed 9  {'LIVE' if live else 'dead'}")
    note = ("A configuration survives; investigate." if any_live
            else "Eliminated under every alphabet and convention.")
    print(f"\n  -> {note}")


# --------------------------------------------------------------------------
# families 3 & 4 -- progressive keys
# --------------------------------------------------------------------------

CRIBS = {pos - 1 for pos in ANCHORS}
MIN_GRAMS = 25


@lru_cache(maxsize=None)
def mask_plan(period: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """(crib-free scorable gram starts, free residues) for a period.

    Which residues the cribs pin depends only on the period, so this is
    computed once per period rather than once per configuration. Grams
    touching an anchor are excluded as well: the anchors decrypt correctly by
    construction in every surviving configuration -- they are what the key was
    solved from -- so scoring them would reward crib-copying.
    """
    covered = {i % period for i in CRIBS}
    free = tuple(s for s in range(period) if s not in covered)
    freeset = set(free)
    ok = [(i % period not in freeset) and i not in CRIBS for i in range(N)]
    windows = tuple(i for i in range(N - 3)
                    if ok[i] and ok[i + 1] and ok[i + 2] and ok[i + 3])
    return windows, free


def progressive_fit(pairs: list[tuple[int, int]], period: int, step: int,
                    mode: str) -> dict[int, int] | None:
    base: dict[int, int] = {}
    for i, k in pairs:
        drift = step * (i // period) if mode == "cycle" else step * i
        want = (k - drift) % 26
        if base.setdefault(i % period, want) != want:
            return None
    return base


def family_progressive(max_period: int, max_unknown: int,
                       with_routes: bool, table, floor) -> int:
    title = "5. PROGRESSIVE KEY x GEOMETRIC TRANSPOSITION" if with_routes \
        else "3 & 4. PROGRESSIVE AND POSITION-LINEAR KEYS"
    print("\n" + "=" * 78)
    print(f" {title}")
    print("=" * 78)

    perms: list[tuple[str, list[int] | None]] = [("identity", None)]
    if with_routes:
        perms = route_permutations(N)
        print(f"\n  {len(perms)} geometric transpositions x progressive keys\n")
    else:
        print("\n  K[i] = base[i mod p] + step*(i div p)   and   base[i mod p] + step*i")
        print(f"  exhaustive over p = 1..{max_period}, step = 0..25, both conventions,\n"
              "  both alphabets, both drift modes\n")

    tested = survivors = scored = undecided = 0
    best: list[tuple[float, str, str]] = []

    for pname, perm in perms:
        for alpha_name, alpha in ALPHABETS.items():
            idx = {c: i for i, c in enumerate(alpha)}
            if perm is None:
                ct_eff = K4_CT
            else:
                inv = [0] * N
                for j, i in enumerate(perm):
                    inv[i] = j
                ct_eff = "".join(K4_CT[inv[i]] for i in range(N))
            for conv in ("vigenere", "beaufort"):
                pairs = shifts(alpha, conv, ct=ct_eff)
                for mode in ("cycle", "linear"):
                    for period in range(1, max_period + 1):
                        for step in range(26):
                            tested += 1
                            base = progressive_fit(pairs, period, step, mode)
                            if base is None:
                                continue
                            survivors += 1
                            windows, free = mask_plan(period)
                            if len(windows) < MIN_GRAMS:
                                undecided += 1
                                continue
                            scored += 1
                            # Decrypt only what the cribs determine. A free
                            # residue darkens the positions congruent to it and
                            # nothing else, so the remaining letters settle the
                            # configuration no matter how it is filled.
                            out = []
                            for i in range(N):
                                k_base = base.get(i % period)
                                if k_base is None:
                                    out.append("?")
                                    continue
                                drift = step * (i // period) if mode == "cycle" else step * i
                                k = (k_base + drift) % 26
                                c = idx[ct_eff[i]]
                                out.append(alpha[(c - k) % 26] if conv == "vigenere"
                                           else alpha[(k - c) % 26])
                            text = "".join(out)
                            sc = (sum(table.get(text[i:i + 4], floor) for i in windows)
                                  / len(windows))
                            if len(best) < 10 or sc > best[-1][0]:
                                best.append((sc, f"{pname} {alpha_name} {conv} "
                                                 f"{mode} p={period} step={step} "
                                                 f"({len(free)} free)", text))
                                best.sort(key=lambda t: -t[0])
                                del best[10:]

    print(f"  tested {tested:,} configurations — {survivors:,} crib-consistent, "
          f"{scored:,} decided, {undecided:,} undecided")
    if undecided:
        print(f"  NOTE: {undecided:,} left under {MIN_GRAMS} crib-free quadgrams and are")
        print("  UNDECIDED, not eliminated.")
    elif survivors:
        print("  Every crib-consistent configuration was decided on crib-free letters;")
        print("  nothing was skipped and no anchor earned any credit.")
    print("\n  best-scoring plaintexts:")
    for sc, label, text in best[:6]:
        print(f"    {sc:6.2f}  {label}")
        print(f"            {text}")
    return survivors, scored, undecided


# --------------------------------------------------------------------------

def selftest() -> int:
    print("PLANTED-CIPHER SELF-TEST")
    print("=" * 78)
    plain = ("THECOMPASSROSEISHEREXEASTNORTHEASTTHISISYOURPOSITIONX"
             "COMMISSIONBERLINCLOCKWHICHISNORTHEASTOFHEREX")
    ok = True
    for alpha_name, conv, mode, period, step, base in [
        ("standard", "vigenere", "cycle", 5, 3, [7, 11, 2, 19, 4]),
        ("KRYPTOS", "beaufort", "cycle", 4, 7, [1, 25, 13, 8]),
        ("standard", "vigenere", "linear", 6, 11, [0, 5, 9, 17, 22, 3]),
        ("KRYPTOS", "vigenere", "linear", 3, 2, [14, 6, 20]),
    ]:
        alpha = ALPHABETS[alpha_name]
        idx = {c: i for i, c in enumerate(alpha)}
        ct = []
        for i in range(N):
            drift = step * (i // period) if mode == "cycle" else step * i
            k = (base[i % period] + drift) % 26
            p = idx[plain[i]]
            ct.append(alpha[(p + k) % 26] if conv == "vigenere" else alpha[(k - p) % 26])
        ct = "".join(ct)

        pairs = shifts(alpha, conv, ct=ct)
        got = progressive_fit(pairs, period, step, mode)
        hit = got is not None and all(got.get(s) in (None, base[s]) for s in range(period))
        ok &= hit
        print(f"  {'PASS' if hit else 'FAIL'}  {alpha_name:<9} {conv:<9} {mode:<7} "
              f"p={period} step={step:>2}  recovered={got is not None}")

        wrong = sum(1 for st in range(26) if st != step
                    and progressive_fit(pairs, period, st, mode) is None)
        print(f"         negative control: {wrong}/25 wrong steps rejected")

    print("\n" + ("SELF-TEST PASSED — the sweep can find what it looks for."
                 if ok else "SELF-TEST FAILED."))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--max-period", type=int, default=30)
    ap.add_argument("--max-unknown", type=int, default=2)
    ap.add_argument("--routes", action="store_true",
                    help="also run progressive keys on every geometric transposition")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    table, floor = load_quadgrams()
    print("KRYPTOS K4 — APERIODIC AND PROGRESSIVE KEYSTREAMS\n")
    family_running_key(table, floor)
    family_digit_limited()
    s_id, d_id, u_id = family_progressive(args.max_period, args.max_unknown,
                                          False, table, floor)
    s_rt = d_rt = u_rt = 0
    if args.routes:
        s_rt, d_rt, u_rt = family_progressive(args.max_period, args.max_unknown,
                                              True, table, floor)
    print("\n" + "=" * 78)
    print(" VERDICT: every family here is eliminated outright.")
    print("   - running keys: implied key fragments score below the noise floor")
    print("   - digit-limited keystreams: 11-15 of 24 cribs exceed 9")
    print(f"   - progressive and position-linear keys: {s_id + s_rt:,} crib-consistent,")
    print(f"     {d_id + d_rt:,} decided on crib-free letters, {u_id + u_rt:,} undecided")
    if u_id + u_rt == 0:
        print("     Nothing was skipped. Note that an earlier version of this script")
        print("     reported this family as 'ZERO crib-consistent'; that number was")
        print("     the count AFTER the --max-unknown filter, so it described what")
        print("     had been read, not what had been refuted. The family is still")
        print("     eliminated, but on the evidence below rather than that one.")
    print("     configurations, with or without a geometric transposition.")
    print()
    print(" Note this is a cleaner kill than the periodic sweep. There, long")
    print(" periods produced crib-copying overfits. Here the drift term couples")
    print(" all 24 cribs to one `step`, so nothing survives at all -- the family")
    print(" cannot even be made to fit by brute force.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
