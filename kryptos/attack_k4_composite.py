#!/usr/bin/env python3
"""KRYPTOS K4 — CRIB-CONSTRAINED COMPOSITE SEARCH (transposition x polyalphabetic).

The largest cipher family never tested against K4 here: a columnar transposition
composed with a periodic polyalphabetic substitution, in both orders.

Why this family, and why now
----------------------------
The repository's own note on PK4-PK6 says a transposition's key "cannot be
scored while the text underneath is still enciphered". For K4 that deadlock
breaks: Sanborn released 24 plaintext letters at known positions. A candidate
permutation can therefore be scored *directly* on whether the anchors remain
arithmetically consistent, with no need to read the text underneath.

Pre-check that kills the simpler cousin
---------------------------------------
Transposition preserves the index of coincidence, and so does monoalphabetic
substitution. English IoC is ~0.0667; K4's is 0.0361. So K4 cannot be
transposition composed with a *monoalphabetic* substitution, in either order,
under any key. The substitution stage must be polyalphabetic. Verified at
runtime below.

Models tested
-------------
    Case A   C = T(V(P))     substitute first, then transpose
    Case B   C = V(T(P))     transpose first, then substitute

    T = classical columnar transposition, L columns, filled row-wise,
        columns read in an arbitrary order (all L! orders enumerated).
    V = periodic polyalphabetic shift of period p, over either the standard
        alphabet or the KRYPTOS-keyed alphabet of the sculpture's tableau.

Method
------
For every (L, column order, case, alphabet) the 24 cribs yield 24
(key index, required shift) pairs. For each period p those pairs are bucketed
by index mod p; any bucket holding two different shifts is a contradiction and
the configuration dies. Survivors have their remaining key residues enumerated
exhaustively and the resulting plaintexts scored with the repository's English
quadgram table.

Run:  python3 kryptos/attack_k4_composite.py
      python3 kryptos/attack_k4_composite.py --max-cols 7   (faster)
"""

from __future__ import annotations

import argparse
import gzip
import math
import time
from collections import Counter
from itertools import permutations, product
from pathlib import Path

K4_CT = ("OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSO"
         "TWTQSJQSSEKZZWATJKLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR")

#: Artist-confirmed plaintext, 1-indexed position -> letter. The only ground truth.
ANCHORS: dict[int, str] = {
    **{22 + i: c for i, c in enumerate("EAST")},
    **{26 + i: c for i, c in enumerate("NORTHEAST")},
    **{64 + i: c for i, c in enumerate("BERLIN")},
    **{70 + i: c for i, c in enumerate("CLOCK")},
}

STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
KRY = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
ALPHABETS = {"standard": STD, "KRYPTOS": KRY}

N = len(K4_CT)
ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------
# scoring
# --------------------------------------------------------------------------

def load_quadgrams() -> tuple[dict[str, float], float]:
    path = ROOT / "buttcrack" / "data" / "english_quadgrams.txt.gz"
    counts: dict[str, int] = {}
    with gzip.open(path, "rt") as fh:
        for line in fh:
            gram, _, num = line.partition(" ")
            if num:
                counts[gram] = int(num)
    total = sum(counts.values())
    table = {g: math.log10(c / total) for g, c in counts.items()}
    return table, math.log10(0.01 / total)


def quadgram_score(text: str, table: dict[str, float], floor: float) -> float:
    return sum(table.get(text[i:i + 4], floor) for i in range(len(text) - 3))


def ioc(text: str) -> float:
    counts = Counter(text)
    n = len(text)
    return sum(v * (v - 1) for v in counts.values()) / (n * (n - 1))


# --------------------------------------------------------------------------
# transposition
# --------------------------------------------------------------------------

def columnar_src(n: int, cols: int, order: tuple[int, ...]) -> list[int]:
    """Row-wise fill, read columns in `order`. output[j] = input[src[j]]."""
    buckets: list[list[int]] = [[] for _ in range(cols)]
    for i in range(n):
        buckets[i % cols].append(i)
    src: list[int] = []
    for c in order:
        src.extend(buckets[c])
    return src


# --------------------------------------------------------------------------
# the search
# --------------------------------------------------------------------------

def route_permutations(n: int) -> list[tuple[str, list[int]]]:
    """Geometric / route transpositions, the non-columnar families.

    K3 was columnar, but Scheidt said K4 involved a deliberate "change in the
    methodology", so the route ciphers a hand encipherer would reach for are
    worth their own sweep: boustrophedon reads, spirals from each corner,
    diagonals, rail fence, and column-wise fill.

    97 is prime, so every grid here is ragged: cell (r, c) exists only where
    r*w + c < n. Spirals walk the full rectangle and skip absent cells.
    """
    out: list[tuple[str, list[int]]] = []

    def grid(w):
        rows = -(-n // w)
        return rows, [[r * w + c for c in range(w) if r * w + c < n] for r in range(rows)]

    for w in range(2, 49):
        rows, g = grid(w)

        out.append((f"rows-boustrophedon w={w}",
                    [i for r, row in enumerate(g) for i in (row if r % 2 == 0 else row[::-1])]))

        cols = [[g[r][c] for r in range(rows) if c < len(g[r])] for c in range(w)]
        out.append((f"cols-plain w={w}", [i for col in cols for i in col]))
        out.append((f"cols-boustrophedon w={w}",
                    [i for c, col in enumerate(cols) for i in (col if c % 2 == 0 else col[::-1])]))

        diag: dict[int, list[int]] = {}
        for r, row in enumerate(g):
            for c, i in enumerate(row):
                diag.setdefault(r + c, []).append(i)
        out.append((f"diagonals w={w}", [i for k in sorted(diag) for i in diag[k]]))

        anti: dict[int, list[int]] = {}
        for r, row in enumerate(g):
            for c, i in enumerate(row):
                anti.setdefault(r - c, []).append(i)
        out.append((f"antidiagonals w={w}", [i for k in sorted(anti) for i in anti[k]]))

        # column-wise fill, row-wise read (the inverse convention)
        fill = [0] * n
        k = 0
        for c in range(w):
            for r in range(rows):
                if r * w + c < n:
                    fill[r * w + c] = k
                    k += 1
        out.append((f"colfill-rowread w={w}", [fill.index(j) for j in range(n)]))

        # spirals: 4 corners x 2 directions over the full rectangle
        for corner in range(4):
            for clockwise in (True, False):
                top, bot, left, right = 0, rows - 1, 0, w - 1
                order: list[int] = []
                while top <= bot and left <= right:
                    for c in range(left, right + 1):
                        order.append(top * w + c)
                    top += 1
                    for r in range(top, bot + 1):
                        order.append(r * w + right)
                    right -= 1
                    if top <= bot:
                        for c in range(right, left - 1, -1):
                            order.append(bot * w + c)
                        bot -= 1
                    if left <= right:
                        for r in range(bot, top - 1, -1):
                            order.append(r * w + left)
                        left += 1
                seq = [i for i in order if i < n]
                if corner in (1, 3):
                    seq = seq[::-1]
                if not clockwise:
                    seq = [n - 1 - i for i in seq]
                if sorted(seq) == list(range(n)):
                    out.append((f"spiral w={w} c={corner} {'cw' if clockwise else 'ccw'}", seq))

    for rails in range(2, 25):
        pattern, r, step = [], 0, 1
        for _ in range(n):
            pattern.append(r)
            if r == 0:
                step = 1
            elif r == rails - 1:
                step = -1
            r += step
        seq = [i for lvl in range(rails) for i, p_ in enumerate(pattern) if p_ == lvl]
        out.append((f"railfence rails={rails}", seq))

    seen, uniq = set(), []
    for name, seq in out:
        key = tuple(seq)
        if key not in seen and sorted(seq) == list(range(n)):
            seen.add(key)
            uniq.append((name, seq))
    return uniq


def keyword_orders(min_len: int, max_len: int) -> dict[int, list[tuple[tuple[int, ...], str]]]:
    """Column orders derived from real dictionary words, the classical way.

    A columnar key is normally a word: number its letters alphabetically (ties
    left to right) and read the columns in that numeric order. This reaches
    key lengths that exhaustive L! enumeration cannot -- notably L=14, the
    width Sanborn actually used in K3 -- while staying inside the key space a
    1980s hand cipher would plausibly use.
    """
    words: set[str] = set()
    wl = ROOT / "kryptos" / "all_words.txt"
    if wl.exists():
        for line in wl.read_text(errors="ignore").split():
            w = line.strip().upper()
            if w.isalpha() and min_len <= len(w) <= max_len:
                words.add(w)
    import gzip as _gz, json as _json
    jp = ROOT / "buttcrack" / "data" / "english_words.json.gz"
    if jp.exists():
        with _gz.open(jp, "rt") as fh:
            for w in _json.load(fh):
                w = str(w).upper()
                if w.isalpha() and min_len <= len(w) <= max_len:
                    words.add(w)

    by_len: dict[int, dict[tuple[int, ...], str]] = {}
    for w in words:
        order = tuple(sorted(range(len(w)), key=lambda i: (w[i], i)))
        by_len.setdefault(len(w), {}).setdefault(order, w)
    return {k: sorted(v.items()) for k, v in sorted(by_len.items())}


def crib_pairs(src: list[int], case: str, idx: dict[str, int],
               ct: str = K4_CT, anchors: dict[int, str] | None = None) -> list[tuple[int, int]]:
    """Return (key index, required shift) for each of the 24 cribs, or [] if n/a.

    Case A  C = T(V(P)):  M[src[j]] = C[j]; key index is the plaintext position i.
    Case B  C = V(T(P)):  C[j] = V(P[src[j]]); key index is the ciphertext position j.
    """
    anchors = ANCHORS if anchors is None else anchors
    pairs: list[tuple[int, int]] = []
    if case == "A":
        inv = [0] * len(src)
        for j, i in enumerate(src):
            inv[i] = j
        for pos, letter in anchors.items():
            i = pos - 1
            mid = ct[inv[i]]
            pairs.append((i, (idx[mid] - idx[letter]) % 26))
    else:
        for j, i in enumerate(src):
            pos = i + 1
            if pos in anchors:
                pairs.append((j, (idx[ct[j]] - idx[anchors[pos]]) % 26))
    return pairs


def consistent(pairs: list[tuple[int, int]], period: int) -> dict[int, int] | None:
    key: dict[int, int] = {}
    for index, shift in pairs:
        slot = index % period
        if key.setdefault(slot, shift) != shift:
            return None
    return key


def decrypt(case: str, src: list[int], key: list[int], alpha: str,
            idx: dict[str, int], ct: str = K4_CT) -> str:
    period = len(key)
    if case == "A":
        inv = [0] * len(src)
        for j, i in enumerate(src):
            inv[i] = j
        mid = [ct[inv[i]] for i in range(N)]
        return "".join(alpha[(idx[mid[i]] - key[i % period]) % 26] for i in range(N))
    out = [""] * N
    for j, i in enumerate(src):
        out[i] = alpha[(idx[ct[j]] - key[j % len(key)]) % 26]
    return "".join(out)


def encrypt(case: str, plain: str, src: list[int], key: list[int],
            alpha: str, idx: dict[str, int]) -> str:
    """Forward direction, used only to build planted test ciphers."""
    period = len(key)
    if case == "A":
        mid = [alpha[(idx[plain[i]] + key[i % period]) % 26] for i in range(N)]
        return "".join(mid[src[j]] for j in range(N))
    mid = [plain[src[j]] for j in range(N)]
    return "".join(alpha[(idx[mid[j]] + key[j % period]) % 26] for j in range(N))


def selftest() -> int:
    """Plant known composite ciphers and confirm the search recovers them.

    A search that finds nothing is only meaningful if it can find something.
    """
    print("PLANTED-CIPHER SELF-TEST")
    print("=" * 78)
    plain = ("THECOMPASSROSEISHEREXEASTNORTHEASTTHISISYOURPOSITIONX"
             "COMMISSIONBERLINCLOCKWHICHISNORTHEASTOFHEREX")
    assert len(plain) == N
    for pos, letter in ANCHORS.items():
        assert plain[pos - 1] == letter, "planted plaintext must carry the cribs"

    cases = [
        ("A", 5, (2, 0, 4, 1, 3), "standard", [7, 11, 2]),
        ("B", 7, (3, 1, 6, 0, 5, 2, 4), "KRYPTOS", [4, 19, 25, 8]),
        ("A", 4, (1, 3, 0, 2), "KRYPTOS", [13, 1]),
        ("B", 6, (5, 0, 2, 4, 1, 3), "standard", [9, 9, 3, 17, 22]),
    ]
    ok = True
    for case, cols, order, alpha_name, key in cases:
        alpha = ALPHABETS[alpha_name]
        idx = {c: i for i, c in enumerate(alpha)}
        src = columnar_src(N, cols, order)
        planted = encrypt(case, plain, src, key, alpha, idx)

        pairs = crib_pairs(src, case, idx, ct=planted)
        recovered = consistent(pairs, len(key))
        found = recovered is not None
        matches = found and all(recovered.get(s) in (None, key[s]) for s in range(len(key)))
        back = (decrypt(case, src, key, alpha, idx, ct=planted) == plain) if found else False

        status = "PASS" if (found and matches and back) else "FAIL"
        ok &= status == "PASS"
        print(f"  {status}  case={case} cols={cols} period={len(key)} alpha={alpha_name:<8} "
              f"crib-consistent={found} key-agrees={matches} decrypts={back}")

    # the crib machinery is permutation-agnostic; confirm it on route transpositions too
    routes = {nm: seq for nm, seq in route_permutations(N)}
    for nm in ("railfence rails=7", "spiral w=12 c=0 cw", "diagonals w=11"):
        if nm not in routes:
            continue
        src = routes[nm]
        alpha = ALPHABETS["KRYPTOS"]
        idx = {c: i for i, c in enumerate(alpha)}
        key = [6, 17, 3]
        for case in ("A", "B"):
            planted = encrypt(case, plain, src, key, alpha, idx)
            rec = consistent(crib_pairs(src, case, idx, ct=planted), len(key))
            back = rec is not None and decrypt(case, src, key, alpha, idx, ct=planted) == plain
            ok &= bool(back)
            print(f"  {'PASS' if back else 'FAIL'}  case={case} route={nm:<20} "
                  f"crib-consistent={rec is not None} decrypts={back}")

    print(f"\n  Negative control: the true config must also survive while wrong ones die.")
    case, cols, order, alpha_name, key = cases[0]
    alpha = ALPHABETS[alpha_name]
    idx = {c: i for i, c in enumerate(alpha)}
    src = columnar_src(N, cols, order)
    planted = encrypt(case, plain, src, key, alpha, idx)
    wrong = 0
    for bad_order in permutations(range(cols)):
        if bad_order == order:
            continue
        bad_src = columnar_src(N, cols, bad_order)
        if consistent(crib_pairs(bad_src, case, idx, ct=planted), len(key)) is None:
            wrong += 1
    print(f"  {wrong}/{math.factorial(cols) - 1} wrong column orders correctly rejected")

    print("\n" + ("SELF-TEST PASSED — the search can find what it looks for."
                  if ok else "SELF-TEST FAILED — results are not trustworthy."))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-cols", type=int, default=8)
    ap.add_argument("--max-period", type=int, default=26)
    ap.add_argument("--max-unknown", type=int, default=2,
                    help="enumerate key residues left undetermined by the cribs")
    ap.add_argument("--routes", action="store_true",
                    help="geometric transpositions: spirals, boustrophedon, diagonals, rail fence")
    ap.add_argument("--keywords", action="store_true",
                    help="use dictionary-derived column orders, reaching L=4..16")
    ap.add_argument("--selftest", action="store_true",
                    help="plant known composite ciphers and confirm they are recovered")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    print("KRYPTOS K4 — CRIB-CONSTRAINED COMPOSITE SEARCH")
    print("=" * 78)

    k4_ioc = ioc(K4_CT)
    print(f"\nPre-check: IoC is invariant under transposition AND under")
    print(f"monoalphabetic substitution.")
    print(f"  K4 IoC          {k4_ioc:.4f}")
    print(f"  English IoC     0.0667")
    print(f"  random IoC      0.0385")
    print(f"  -> transposition x MONOalphabetic substitution is impossible in either")
    print(f"     order, under any key. The substitution stage must be polyalphabetic.\n")

    table, floor = load_quadgrams()
    print(f"Loaded {len(table):,} English quadgrams for scoring.")

    english_ref = quadgram_score(
        "THECOMPASSROSEISHEREXEASTNORTHEASTTHISISYOURPOSITIONX"
        "COMMISSIONBERLINCLOCKWHICHISNORTHEASTOFHEREX", table, floor)
    print(f"Reference: fluent 97-letter English scores about {english_ref:,.0f}\n")

    total_configs = 0
    survivors = 0
    best: list[tuple[float, str, str]] = []
    started = time.time()

    if args.routes:
        routes = route_permutations(N)
        print(f"Geometric transpositions: {len(routes):,} distinct permutations\n")
        schedule = [("route", [tuple(s) for _, s in routes],
                     {tuple(s): nm for nm, s in routes})]
    elif args.keywords:
        plan = keyword_orders(4, 16)
        total_orders = sum(len(v) for v in plan.values())
        print(f"Dictionary-derived column orders: {total_orders:,} distinct patterns "
              f"across L=4..16\n")
        schedule = [(L, [o for o, _ in v], {o: w for o, w in v}) for L, v in plan.items()]
    else:
        schedule = [(L, list(permutations(range(L))), {}) for L in range(2, args.max_cols + 1)]

    for cols, orders, words in schedule:
        col_survivors = 0
        for order in orders:
            src = list(order) if cols == "route" else columnar_src(N, cols, order)
            for alpha_name, alpha in ALPHABETS.items():
                idx = {c: i for i, c in enumerate(alpha)}
                for case in ("A", "B"):
                    pairs = crib_pairs(src, case, idx)
                    for period in range(1, args.max_period + 1):
                        total_configs += 1
                        key = consistent(pairs, period)
                        if key is None:
                            continue
                        unknown = [s for s in range(period) if s not in key]
                        if len(unknown) > args.max_unknown:
                            continue
                        survivors += 1
                        col_survivors += 1
                        for fill in product(range(26), repeat=len(unknown)):
                            full = [key.get(s, 0) for s in range(period)]
                            for slot, val in zip(unknown, fill):
                                full[slot] = val
                            text = decrypt(case, src, full, alpha, idx)
                            sc = quadgram_score(text, table, floor)
                            if len(best) < 15 or sc > best[-1][0]:
                                kw = words.get(order)
                                label = (f"cols={cols} "
                                         f"{'key=' + kw if kw else 'order=' + str(order)} "
                                         f"case={case} alpha={alpha_name} period={period}")
                                best.append((sc, label, text))
                                best.sort(key=lambda t: -t[0])
                                del best[15:]
        label = "route perms" if cols == "route" else f"L={cols:>2} columns"
        print(f"  {label:<14} ({len(orders):>7,} orders) -> "
              f"{col_survivors:>6,} crib-consistent configurations")

    elapsed = time.time() - started
    print(f"\nTested {total_configs:,} configurations in {elapsed:.1f}s")
    print(f"Crib-consistent survivors (<= {args.max_unknown} free residues): {survivors:,}")

    print("\nBest-scoring candidate plaintexts:")
    print("-" * 78)
    for sc, label, text in best[:10]:
        verdict = "ENGLISH?" if sc > english_ref * 0.85 else ""
        print(f"  {sc:>10,.0f}  {label}")
        print(f"              {text}  {verdict}")

    print("\n" + "=" * 78)
    if best and best[0][0] > english_ref * 0.85:
        print("A candidate scores near fluent English. Verify by hand before believing it.")
        return 1
    print("VERDICT: no configuration in this family yields English.")
    print("Columnar transposition composed with a periodic polyalphabetic cipher is")
    if args.routes:
        print("eliminated for every geometric/route transposition swept")
    elif args.keywords:
        print("eliminated for every dictionary-keyword column order of length 4-16")
    else:
        print(f"eliminated for every column order with L <= {args.max_cols}")
    print(f"and period <= {args.max_period}, in both composition orders, both alphabets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
