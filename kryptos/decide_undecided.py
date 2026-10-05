#!/usr/bin/env python3
"""DECIDE THE CONFIGURATIONS THE COMPOSITE SWEEP SKIPPED.

Why this exists
---------------
`attack_k4_composite.py` filters on `--max-unknown`: a configuration whose key
the 24 cribs leave with more than N free residues is dropped before it is ever
read, because enumerating the fills costs 26**N decrypts. Those drops were then
counted alongside genuine refutations. They are not the same thing. A
configuration that was skipped has not been eliminated -- it is undecided, and
the honest sweep reports the two separately.

The route sweep hid 29 such configurations behind a reported elimination. At
L = 4..16 over dictionary column orders the skipped set is far larger and 26**N
enumeration is hopeless.

The method, which needs no enumeration at all
---------------------------------------------
Every plaintext position depends on exactly one key residue. So decrypt twice,
once filling the free residues with 0 and once with 1. Positions that depend on
a free residue shift by one letter and therefore differ; positions the cribs
determine are identical. The disagreement set is *exactly* the undetermined
positions -- this is an identity, not a sample.

Score only quadgrams that avoid those positions, and also avoid the 24 anchors
so that crib-copying earns no credit. If the determined letters are not
English, no assignment of the free residues can make them English: those
letters do not move.

Run:  python3 kryptos/decide_undecided.py --selftest
      python3 kryptos/decide_undecided.py --keywords
      python3 kryptos/decide_undecided.py --routes
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from attack_k4_composite import (  # noqa: E402
    ALPHABETS, ANCHORS, K4_CT, N, columnar_src, consistent, crib_pairs,
    decrypt, encrypt, keyword_orders, load_quadgrams, route_permutations,
)

CRIBS = {pos - 1 for pos in ANCHORS}
MIN_GRAMS = 20


def determined_mask(case: str, src: list[int], key: dict[int, int], period: int,
                    alpha: str, idx: dict[str, int], ct: str = K4_CT) -> list[bool]:
    """True where the plaintext letter is fixed by the cribs alone.

    Two decrypts with free residues set to 0 and to 1. A position fed by a free
    residue must differ between them; one fed by a determined residue cannot.
    """
    k0 = [key.get(s, 0) for s in range(period)]
    k1 = [key.get(s, 1) for s in range(period)]
    a = decrypt(case, src, k0, alpha, idx, ct=ct)
    b = decrypt(case, src, k1, alpha, idx, ct=ct)
    return [a[i] == b[i] for i in range(N)]


def masked_windows(mask: list[bool], skip_cribs: bool = True) -> list[int]:
    ok = [mask[i] and not (skip_cribs and i in CRIBS) for i in range(N)]
    return [i for i in range(N - 3)
            if ok[i] and ok[i + 1] and ok[i + 2] and ok[i + 3]]


def masked_score(text: str, windows, table, floor) -> float:
    return sum(table.get(text[i:i + 4], floor) for i in windows) / len(windows)


def exact_best(case: str, src: list[int], key: dict[int, int], period: int,
               alpha: str, idx: dict[str, int], table, floor) -> tuple[float, str]:
    """Exact maximum crib-free score over EVERY fill of the free residues.

    The last resort for configurations the mask cannot decide because too few
    determined letters survive. No sampling and no cap: this enumerates the
    whole fill space, so a low result here is a refutation of all 26**free
    keys at once, not of a shortlist.
    """
    from itertools import product
    free = [s for s in range(period) if s not in key]
    scorable = [i for i in range(N - 3)
                if not any(j in CRIBS for j in range(i, i + 4))]
    best_sc, best_txt = None, ""
    for fill in product(range(26), repeat=len(free)):
        kk = [key.get(t, 0) for t in range(period)]
        for s, val in zip(free, fill):
            kk[s] = val
        txt = decrypt(case, src, kk, alpha, idx)
        sc = sum(table.get(txt[i:i + 4], floor) for i in scorable)
        if best_sc is None or sc > best_sc:
            best_sc, best_txt = sc, txt
    return best_sc / len(scorable), best_txt


def best_possible_threshold(table, floor) -> float:
    eng, noise = reference_scores(table, floor)
    return noise + 0.80 * (eng - noise)


def reference_scores(table, floor) -> tuple[float, float]:
    plain = ("THECOMPASSROSEISHEREXEASTNORTHEASTTHISISYOURPOSITIONX"
             "COMMISSIONBERLINCLOCKWHICHISNORTHEASTOFHEREX")
    full = masked_windows([True] * N)
    return (masked_score(plain, full, table, floor),
            masked_score(K4_CT, full, table, floor))


def run(schedule, max_unknown: int, max_period: int, table, floor, label: str,
        exact: bool = False, exact_cap: int = 12_000_000):
    eng, noise = reference_scores(table, floor)
    print(f"\n  fluent English {eng:.2f} per crib-free quadgram, "
          f"ciphertext {noise:.2f}")
    print(f"  deciding only what --max-unknown {max_unknown} would have skipped\n")

    tested = consistent_n = skipped = decided = undecided = 0
    best: list[tuple[float, str, str]] = []
    hard: list = []
    started = time.time()

    for cols, orders, words in schedule:
        for order in orders:
            src = list(order) if cols == "route" else columnar_src(N, cols, order)
            for alpha_name, alpha in ALPHABETS.items():
                idx = {c: i for i, c in enumerate(alpha)}
                for case in ("A", "B"):
                    pairs = crib_pairs(src, case, idx)
                    for period in range(1, max_period + 1):
                        tested += 1
                        key = consistent(pairs, period)
                        if key is None:
                            continue
                        consistent_n += 1
                        free = [s for s in range(period) if s not in key]
                        if len(free) <= max_unknown:
                            continue          # the main sweep already read it
                        skipped += 1
                        mask = determined_mask(case, src, key, period, alpha, idx)
                        windows = masked_windows(mask)
                        if len(windows) < MIN_GRAMS:
                            kw = words.get(order)
                            tag = f"key={kw}" if kw else f"order={order}"
                            hard.append((f"cols={cols} {tag} case={case} "
                                         f"alpha={alpha_name} p={period}",
                                         case, src, dict(key), period, alpha,
                                         dict(idx), len(free), len(windows)))
                            undecided += 1
                            continue
                        decided += 1
                        text = decrypt(case, src,
                                       [key.get(s, 0) for s in range(period)],
                                       alpha, idx)
                        shown = "".join(text[i] if mask[i] else "?" for i in range(N))
                        sc = masked_score(text, windows, table, floor)
                        if len(best) < 10 or sc > best[-1][0]:
                            kw = words.get(order)
                            tag = f"key={kw}" if kw else f"order={order}"
                            best.append((sc, f"cols={cols} {tag} case={case} "
                                             f"alpha={alpha_name} p={period} "
                                             f"({len(free)} free, {len(windows)} grams)",
                                         shown))
                            best.sort(key=lambda t: -t[0])
                            del best[10:]

    print(f"  tested {tested:,} configurations in {time.time() - started:.1f}s")
    print(f"  crib-consistent   {consistent_n:,}")
    print(f"  of those, skipped by the --max-unknown {max_unknown} filter: {skipped:,}")
    print(f"  now decided on determined letters: {decided:,}")
    print(f"  too thin for masking (under {MIN_GRAMS} crib-free grams): {undecided:,}")

    resolved = 0
    if hard and exact:
        print(f"\n  EXACT STAGE — enumerating every fill for the {len(hard)} thin cases")
        print("  " + "-" * 74)
        for lab, case, src, key, period, alpha, idx, nfree, ngrams in hard:
            cost = 26 ** nfree
            if cost > exact_cap:
                print(f"    SKIP  {lab}: {nfree} free = {cost:,} fills, over the cap")
                continue
            sc, txt = exact_best(case, src, key, period, alpha, idx, table, floor)
            resolved += 1
            print(f"    {sc:6.2f}  {lab} ({nfree} free, ALL {cost:,} fills enumerated)")
            print(f"            {txt}")
            if sc > best_possible_threshold(table, floor):
                print("            ^^ APPROACHES ENGLISH — verify by hand")
        undecided -= resolved
        print(f"\n  exact stage decided {resolved} of {len(hard)}; "
              f"{undecided} still undecided")
    elif hard:
        print(f"  (run with --exact to enumerate these {len(hard)} exhaustively)")

    if best:
        print("\n  best of the previously-skipped set "
              "('?' = undetermined by the cribs):")
        print("  " + "-" * 74)
        for sc, lab, text in best[:6]:
            print(f"    {sc:6.2f}  {lab}")
            print(f"            {text}")
        top = best[0][0]
        pct = (top - noise) / (eng - noise) * 100
        print(f"\n  best {top:.2f}; English {eng:.2f}, noise {noise:.2f} — "
              f"{pct:.0f}% of the way from noise to English")

    print("\n" + "=" * 78)
    if undecided:
        print(f" PARTIAL: {decided:,} decided, {undecided:,} still undecided.")
        return 1
    if best and best[0][0] > noise + 0.80 * (eng - noise):
        print(" A previously-skipped configuration approaches English. Verify by hand.")
        return 1
    print(f" VERDICT: all {skipped:,} configurations the {label} sweep skipped are now")
    print(" decided, and none yields English. The elimination claim for this family")
    print(" no longer rests on anything that went unread.")
    return 0


def selftest() -> int:
    """The mask must be exact and the score must find a planted cipher."""
    table, floor = load_quadgrams()
    plain = ("THECOMPASSROSEISHEREXEASTNORTHEASTTHISISYOURPOSITIONX"
             "COMMISSIONBERLINCLOCKWHICHISNORTHEASTOFHEREX")
    print("SELF-TEST — masking identity and planted recovery")
    print("=" * 78)
    ok = True

    print("\n[1] the two-fill mask must be exactly the undetermined set")
    for cols, order, case, period in [(7, (3, 1, 4, 0, 6, 2, 5), "A", 23),
                                      (9, (2, 7, 0, 5, 8, 1, 6, 3, 4), "B", 25),
                                      (5, (4, 0, 3, 1, 2), "A", 26)]:
        src = columnar_src(N, cols, order)
        alpha = ALPHABETS["KRYPTOS"]
        idx = {c: i for i, c in enumerate(alpha)}
        # plant a real cipher so the configuration is genuinely crib-consistent;
        # against raw K4 these configs are contradicted and the test would be
        # vacuous.
        planted = encrypt(case, plain, src,
                          [(5 * s + 2) % 26 for s in range(period)], alpha, idx)
        key = consistent(crib_pairs(src, case, idx, ct=planted), period)
        if key is None:
            print(f"  FAIL  cols={cols} case={case} p={period}: planted cipher "
                  f"not crib-consistent")
            ok = False
            continue
        mask = determined_mask(case, src, key, period, alpha, idx, ct=planted)
        # ground truth: a position is determined iff its key residue is known
        if case == "A":
            truth = [(i % period) in key for i in range(N)]
        else:
            truth = [False] * N
            for j, i in enumerate(src):
                truth[i] = (j % period) in key
        good = mask == truth
        ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  cols={cols} case={case} p={period}: "
              f"{sum(mask)} determined, mask matches ground truth: {good}")

    print("\n[2] a planted cipher must be recoverable from masked evidence alone")
    for cols, order, case, period in [(7, (3, 1, 4, 0, 6, 2, 5), "A", 23),
                                      (9, (2, 7, 0, 5, 8, 1, 6, 3, 4), "B", 25)]:
        src = columnar_src(N, cols, order)
        alpha = ALPHABETS["KRYPTOS"]
        idx = {c: i for i, c in enumerate(alpha)}
        key = [(5 * s + 2) % 26 for s in range(period)]
        ct = encrypt(case, plain, src, key, alpha, idx)
        solved = consistent(crib_pairs(src, case, idx, ct=ct), period)
        assert solved is not None
        mask = determined_mask(case, src, solved, period, alpha, idx, ct=ct)
        windows = masked_windows(mask)
        text = decrypt(case, src, [solved.get(s, 0) for s in range(period)],
                       alpha, idx, ct=ct)
        exact = all(text[i] == plain[i] for i in range(N) if mask[i])
        sc = masked_score(text, windows, table, floor)
        eng, noise = reference_scores(table, floor)
        close = sc > noise + 0.80 * (eng - noise)
        ok &= exact and close
        print(f"  {'PASS' if exact and close else 'FAIL'}  cols={cols} case={case} "
              f"p={period}: {len(windows)} grams, score {sc:.2f} "
              f"(English {eng:.2f}, noise {noise:.2f}), determined letters exact: {exact}")

    print("\n" + ("SELF-TEST PASSED — the mask is exact and masked scoring recovers"
                  "\nplanted ciphers the enumeration filter would have thrown away."
                  if ok else "SELF-TEST FAILED."))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--routes", action="store_true")
    ap.add_argument("--keywords", action="store_true")
    ap.add_argument("--exhaustive", action="store_true")
    ap.add_argument("--max-cols", type=int, default=9)
    ap.add_argument("--max-unknown", type=int, default=2)
    ap.add_argument("--max-period", type=int, default=26)
    ap.add_argument("--exact", action="store_true",
                    help="enumerate every fill for cases masking cannot decide")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    table, floor = load_quadgrams()
    print("DECIDING WHAT THE COMPOSITE SWEEP SKIPPED")
    print("=" * 78)
    if args.routes:
        routes = route_permutations(N)
        print(f"\n  route/geometric transpositions: {len(routes):,}")
        sched = [("route", [tuple(s) for _, s in routes],
                  {tuple(s): nm for nm, s in routes})]
        return run(sched, args.max_unknown, args.max_period, table, floor,
                   "route", args.exact)
    if args.keywords:
        plan = keyword_orders(4, 16)
        total = sum(len(v) for v in plan.values())
        print(f"\n  dictionary column orders: {total:,} patterns across L=4..16")
        sched = [(L, [o for o, _ in v], {o: w for o, w in v})
                 for L, v in plan.items()]
        return run(sched, args.max_unknown, args.max_period, table, floor,
                   "keyword", args.exact)
    if args.exhaustive:
        from itertools import permutations
        print(f"\n  exhaustive column orders L=2..{args.max_cols}")
        sched = [(L, list(permutations(range(L))), {})
                 for L in range(2, args.max_cols + 1)]
        return run(sched, args.max_unknown, args.max_period, table, floor,
                   "exhaustive", args.exact)
    print("choose --routes, --keywords or --exhaustive (or --selftest)")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
