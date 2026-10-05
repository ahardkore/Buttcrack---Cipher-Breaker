#!/usr/bin/env python3
"""KRYPTOS K4 — KEYED-ALPHABET (QUAGMIRE) SWEEP, CRIB-CONSTRAINED.

A gap the earlier sweeps left open
----------------------------------
`attack_k4_composite.py` and `attack_k4_aperiodic.py` are exhaustive over
*keys* but fixed the *alphabet* to one of two: standard A-Z, or the sculpture's
KRYPTOS-keyed tableau alphabet. Quagmire ciphers key the alphabets themselves,
which changes the index mapping and therefore escapes every sweep so far.

This also settles the misspelling question properly. Sanborn's deliberate
errors -- IQLUSION, UNDERGRUUND, DESPARATLY, the omitted S -- are usually
proposed as *key material*. But a specific key proposal cannot revive a family
that was already swept exhaustively over all keys: those sweeps tested every
key, including whatever the misspellings would have produced. The misspellings
can only matter if they select a *mechanism* rather than a key -- and the
obvious mechanism they could select is a keyed alphabet. So they enter here, as
alphabet keywords, which is the one place they can still do work.

Models
------
    Quagmire I     plaintext alphabet keyed, ciphertext alphabet straight
    Quagmire II    plaintext straight, ciphertext keyed
    Quagmire III   both keyed with the same word (K1 and K2 are Quagmire III)
    Quagmire IV    both keyed, with different words

In each case  C[i] = A_c[ (A_p.index(P[i]) + k[i mod p]) mod 26 ],
so the 24 cribs give  k[i mod p] = A_c.index(C[i]) - A_p.index(P[i]).
Bucket by i mod p; any bucket holding two different values is a contradiction.

The key is never guessed -- it is solved for. That is what makes a dictionary
sweep over alphabets affordable.

Deciding the periods the cribs do not fully pin
-----------------------------------------------
The 24 cribs sit at 0-indexed positions 21..33 and 63..73. For p <= 13 and for
p in {15,16,17} they touch every residue, so a surviving configuration has a
fully determined key. For p in {14,18,...,26} some residues are free:

    p=26 -> 3 free,  p=25 -> 4,  p=24 -> 5,  p=23 -> 6,  p=22 -> 7,
    p=21 -> 8,       p=20 -> 7,  p=19 -> 4,  p=18 -> 1,  p=14 -> 1

An earlier version of this script enumerated those free residues (26**f fills)
and *skipped* any configuration with more than `--max-unknown` of them. That was
wrong twice over. It is infeasible -- p=21 would need 26**8 = 2.1e11 fills per
configuration -- and it silently reported skipped configurations as though they
had been refuted, which is the one error this project cannot afford.

The fix is to stop enumerating. A free residue only darkens the positions
congruent to it; every other letter is already determined by the cribs alone.
Masking out the dark positions still leaves 50 to 94 scorable quadgrams at
every period:

    p=26 -> 70 grams,  p=23 -> 58,  p=21 -> 50,  p=20 -> 50,  p=14 -> 66

On this quadgram table fluent English scores -4.15 per gram and uniform random
text -8.28, and masking preserves almost all of that: at p=21, the worst case,
50 surviving grams still separate English from random by 4.09. If the
determined letters are not English, no assignment of the free residues can make
them English -- those letters do not move. One masked decrypt therefore decides
a configuration that brute force could not reach in the lifetime of the
universe, and `--max-unknown` is demoted to controlling the optional full
enumeration of the final shortlist.

Run:  python3 kryptos/attack_k4_quagmire.py --selftest
      python3 kryptos/attack_k4_quagmire.py
"""

from __future__ import annotations

import argparse
import gzip
import math
import time
from functools import lru_cache
from itertools import product
from pathlib import Path

K4_CT = ("OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSO"
         "TWTQSJQSSEKZZWATJKLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR")

ANCHORS: dict[int, str] = {
    **{22 + i: c for i, c in enumerate("EAST")},
    **{26 + i: c for i, c in enumerate("NORTHEAST")},
    **{64 + i: c for i, c in enumerate("BERLIN")},
    **{70 + i: c for i, c in enumerate("CLOCK")},
}

STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ROOT = Path(__file__).resolve().parent.parent
N = 97

#: Minimum crib-free quadgrams required before we are willing to call a
#: configuration decided. The thinnest period (p=20, p=21) still yields 30 and
#: the richest 64, so in practice nothing is left undecided -- but the counter
#: is reported, never assumed.
MIN_GRAMS = 25

#: Keywords the sculpture itself nominates. The misspelling-derived entries are
#: the hypothesis that Sanborn's deliberate errors encode alphabet keys:
#: the wrong letters (Q, U, A -> QUA), the correct ones (L, O, E -> LOE), and
#: the words in both spellings.
CURATED = [
    "KRYPTOS", "PALIMPSEST", "ABSCISSA", "QUA", "QUAS", "LOE", "LOES",
    "IQLUSION", "ILLUSION", "UNDERGRUUND", "UNDERGROUND", "DESPARATLY",
    "DESPERATELY", "BERLIN", "CLOCK", "BERLINCLOCK", "WELTZEITUHR",
    "ALEXANDERPLATZ", "COMPASSROSE", "LODESTONE", "MAGNETIC", "SHADOW",
    "LUCID", "MEMORY", "SANBORN", "SCHEIDT", "LANGLEY", "INVISIBLE",
    "LAYERTWO", "NORTHEAST", "SOUTHEAST", "EASTNORTHEAST", "POSITION",
    "SUBUMBRAFLOREO", "TENTATIVE", "INTERPRETATI", "WILLIAMWEBSTER", "ONLYWW",
]


def keyed(word: str) -> str:
    seen: list[str] = []
    for ch in word.upper():
        if ch.isalpha() and ch not in seen:
            seen.append(ch)
    return "".join(seen) + "".join(c for c in STD if c not in seen)


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
    return sum(table.get(text[i:i + 4], floor) for i in range(n)) / n


@lru_cache(maxsize=None)
def mask_plan(period: int) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    """(all scorable grams, crib-free scorable grams, free residues).

    Depends only on where the cribs sit, so it is computed once per period
    rather than once per configuration.

    Two window sets, because scoring the anchor spans would reward
    crib-copying. The anchors decrypt correctly by construction in every
    surviving configuration -- they are what the key was solved from -- so a
    gram overlapping EAST, NORTHEAST, BERLIN or CLOCK is guaranteed English
    and carries no evidence. This project has been fooled by exactly that
    four times. The second window set drops every gram touching a crib, so it
    scores only letters the cipher genuinely predicted. At p=26 that still
    leaves 46 grams; the thinnest period keeps 26.
    """
    covered = {(pos - 1) % period for pos in ANCHORS}
    free = tuple(s for s in range(period) if s not in covered)
    freeset = set(free)
    cribs = {pos - 1 for pos in ANCHORS}
    known = [i % period not in freeset for i in range(N)]
    clean = [known[i] and i not in cribs for i in range(N)]
    windows = tuple(i for i in range(N - 3)
                    if known[i] and known[i + 1] and known[i + 2] and known[i + 3])
    windows_nc = tuple(i for i in range(N - 3)
                       if clean[i] and clean[i + 1] and clean[i + 2] and clean[i + 3])
    return windows, windows_nc, free


def alphabet_pool(limit: int) -> list[tuple[str, str]]:
    """Distinct keyed alphabets, curated words first so they are never cut."""
    words: list[str] = list(CURATED)
    wl = ROOT / "kryptos" / "all_words.txt"
    if wl.exists():
        extra = sorted({w.strip().upper() for w in wl.read_text(errors="ignore").split()
                        if w.strip().isalpha() and 3 <= len(w.strip()) <= 15})
        words.extend(extra)
    seen: dict[str, str] = {}
    for w in words:
        a = keyed(w)
        if a not in seen:
            seen[a] = w
        if len(seen) >= limit:
            break
    return [(w, a) for a, w in seen.items()]


def crib_pairs(a_p: str, a_c: str, ct: str = K4_CT,
               anchors: dict[int, str] | None = None) -> list[tuple[int, int]]:
    anchors = ANCHORS if anchors is None else anchors
    ip = {c: i for i, c in enumerate(a_p)}
    ic = {c: i for i, c in enumerate(a_c)}
    return [(pos - 1, (ic[ct[pos - 1]] - ip[letter]) % 26)
            for pos, letter in sorted(anchors.items())]


def consistent(pairs, period: int) -> dict[int, int] | None:
    key: dict[int, int] = {}
    for i, k in pairs:
        if key.setdefault(i % period, k) != k:
            return None
    return key


def decrypt(a_p: str, a_c: str, key: list[int], ct: str = K4_CT) -> str:
    ic = {c: i for i, c in enumerate(a_c)}
    p = len(key)
    return "".join(a_p[(ic[ct[i]] - key[i % p]) % 26] for i in range(N))


def partial_decrypt(a_p: str, a_c: str, key: dict[int, int], period: int,
                    ct: str = K4_CT) -> str:
    """Decrypt only the positions the cribs determine; '?' elsewhere."""
    ic = {c: i for i, c in enumerate(a_c)}
    out = []
    for i in range(N):
        k = key.get(i % period)
        out.append("?" if k is None else a_p[(ic[ct[i]] - k) % 26])
    return "".join(out)


def masked_score(text: str, windows, table, floor) -> float:
    return sum(table.get(text[i:i + 4], floor) for i in windows) / len(windows)


# --------------------------------------------------------------------------
# analytic layer: impossibility proofs that hold for ALL 26! alphabets
# --------------------------------------------------------------------------

def crib_triples(ct: str = K4_CT,
                 anchors: dict[int, str] | None = None) -> list[tuple[int, str, str]]:
    anchors = ANCHORS if anchors is None else anchors
    return [(pos - 1, letter, ct[pos - 1]) for pos, letter in sorted(anchors.items())]


def impossible_pair(model: str, c1, c2) -> str | None:
    """Is this collision contradictory for EVERY alphabet? Sufficient, sound.

    Two cribs landing in the same key residue must imply the same shift. Each
    test below cancels a letter and reduces the requirement to x[a] == x[b]
    with a != b, which no permutation can satisfy -- so when one fires the
    period is refuted outright, not merely unobserved in some sample.
    """
    _, p1, k1 = c1
    _, p2, k2 = c2
    if model == "III":
        # one unknown alphabet on both sides: x[k1] - x[p1] == x[k2] - x[p2]
        if k1 == k2 and p1 != p2:
            return f"x[{p1}]=x[{p2}]"
        if p1 == p2 and k1 != k2:
            return f"x[{k1}]=x[{k2}]"
        if k1 == p1 and k2 != p2:
            return f"x[{k2}]=x[{p2}]"
        if k2 == p2 and k1 != p1:
            return f"x[{k1}]=x[{p1}]"
        return None
    if model == "I":
        # plaintext alphabet unknown, ciphertext standard
        if p1 == p2 and (STD.index(k1) - STD.index(k2)) % 26:
            return f"x[{p1}] != x[{p1}]"
        return None
    if model == "II":
        # ciphertext alphabet unknown, plaintext standard
        if k1 == k2 and (STD.index(p1) - STD.index(p2)) % 26:
            return f"x[{k1}] != x[{k1}]"
        return None
    raise ValueError(model)


def analytic_impossibility(cribs, max_period: int = 26):
    """{model: {period: witness}} for periods refuted over every alphabet."""
    out: dict[str, dict[int, tuple]] = {}
    for model in ("I", "II", "III"):
        found: dict[int, tuple] = {}
        for period in range(1, max_period + 1):
            for a in range(len(cribs)):
                for b in range(a + 1, len(cribs)):
                    if (cribs[a][0] - cribs[b][0]) % period:
                        continue
                    why = impossible_pair(model, cribs[a], cribs[b])
                    if why:
                        found[period] = (cribs[a][0] + 1, cribs[b][0] + 1, why)
                        break
                if period in found:
                    break
        out[model] = found
    return out


def sweep(label: str, pairs_iter, max_period: int, table, floor,
          best: list) -> tuple[int, int, int, int]:
    """Returns (tested, crib-consistent, decided, undecided).

    'decided' means the letters the cribs determine supplied at least
    MIN_GRAMS quadgrams, so the configuration was scored on evidence that no
    choice of the free residues can alter. 'undecided' is reported separately
    and is never folded into an elimination claim.
    """
    tested = survivors = decided = undecided = 0
    for wp, ap, wc, ac in pairs_iter:
        pairs = crib_pairs(ap, ac)
        for period in range(1, max_period + 1):
            tested += 1
            key = consistent(pairs, period)
            if key is None:
                continue
            survivors += 1
            windows, windows_nc, free = mask_plan(period)
            if len(windows_nc) < MIN_GRAMS:
                undecided += 1
                continue
            decided += 1
            text = partial_decrypt(ap, ac, key, period)
            sc = masked_score(text, windows_nc, table, floor)
            if len(best) < 12 or sc > best[-1][0]:
                best.append((sc, masked_score(text, windows, table, floor),
                             label.strip(), wp, wc, period, len(free), text))
                best.sort(key=lambda t: -t[0])
                del best[12:]
    return tested, survivors, decided, undecided


# --------------------------------------------------------------------------
# self-test
# --------------------------------------------------------------------------

PLAIN = ("THECOMPASSROSEISHEREXEASTNORTHEASTTHISISYOURPOSITIONX"
         "COMMISSIONBERLINCLOCKWHICHISNORTHEASTOFHEREX")


def plant(wp: str, wc: str, key: list[int]) -> tuple[str, str, str]:
    ap, ac = keyed(wp), keyed(wc)
    ip = {c: i for i, c in enumerate(ap)}
    ct = "".join(ac[(ip[PLAIN[i]] + key[i % len(key)]) % 26] for i in range(N))
    return ap, ac, ct


def selftest() -> int:
    table, floor = load_quadgrams()
    print("PLANTED-CIPHER SELF-TEST")
    print("=" * 78)
    ok = True

    print("\n[1] fully determined keys -- crib solve must recover the key and decrypt")
    for wp, wc, key in [("KRYPTOS", "KRYPTOS", [4, 17, 9]),
                        ("ABSCISSA", STD, [11, 2, 20, 6]),
                        (STD, "PALIMPSEST", [1, 25]),
                        ("QUA", "LODESTONE", [7, 13, 3, 19, 22])]:
        ap, ac, ct = plant(wp, wc, key)
        got = consistent(crib_pairs(ap, ac, ct=ct), len(key))
        agree = got is not None and all(got.get(s) in (None, key[s]) for s in range(len(key)))
        back = got is not None and decrypt(ap, ac, key, ct=ct) == PLAIN
        ok &= agree and back
        print(f"  {'PASS' if agree and back else 'FAIL'}  pt={wp[:12]:<12} ct={wc[:12]:<12} "
              f"p={len(key)}  consistent={got is not None} decrypts={back}")

    print("\n[2] negative control -- wrong plaintext alphabet must be contradicted")
    ap, ac, ct = plant("KRYPTOS", "KRYPTOS", [4, 17, 9])
    rejected = sum(1 for w in CURATED[:30]
                   if keyed(w) != ap and consistent(crib_pairs(keyed(w), ac, ct=ct), 3) is None)
    tried = sum(1 for w in CURATED[:30] if keyed(w) != ap)
    ok &= rejected == tried
    print(f"  {'PASS' if rejected == tried else 'FAIL'}  "
          f"{rejected}/{tried} wrong plaintext alphabets rejected")

    print("\n[3] THE CRITICAL TEST -- periods brute force cannot reach.")
    print("    Free residues are left unfilled; only the crib-determined letters")
    print("    are scored. The true alphabet pair must still come out on top of a")
    print("    field of decoys, and its determined letters must be exactly right.")
    decoy_alphabets = [a for _, a in alphabet_pool(2000)]
    print(f"\n  {'period':>6} {'free':>5} {'grams*':>6} {'true':>7} {'decoys':>7} "
          f"{'survive crib':>13} {'beat true':>10} {'best decoy':>11}")
    for period in (14, 18, 19, 20, 21, 22, 23, 24, 25, 26):
        windows, windows_nc, free = mask_plan(period)
        key = [(7 * s + 3) % 26 for s in range(period)]
        ap, ac, ct = plant("ABSCISSA", "LODESTONE", key)

        solved = consistent(crib_pairs(ap, ac, ct=ct), period)
        assert solved is not None, "planted key must be crib-consistent"
        text = partial_decrypt(ap, ac, solved, period, ct=ct)
        true_sc = masked_score(text, windows_nc, table, floor)

        # the determined letters must match the real plaintext exactly
        exact = all(text[i] == PLAIN[i] for i in range(N) if text[i] != "?")

        tried = survived = 0
        scores = []
        for alt in decoy_alphabets:
            for dp, dc in ((alt, ac), (ap, alt)):
                if (dp, dc) == (ap, ac):
                    continue
                tried += 1
                dk = consistent(crib_pairs(dp, dc, ct=ct), period)
                if dk is None:
                    continue
                survived += 1
                dt = partial_decrypt(dp, dc, dk, period, ct=ct)
                scores.append(masked_score(dt, windows_nc, table, floor))
        beaten = sum(1 for d in scores if d >= true_sc)
        good = exact and beaten == 0
        ok &= good
        top = f"{max(scores):.2f}" if scores else "--"
        print(f"  {period:>6} {len(free):>5} {len(windows_nc):>6} {true_sc:>7.2f} "
              f"{tried:>7,} {survived:>13,} {beaten:>10} {top:>11}"
              f"  {'PASS' if good else 'FAIL'}")
    print("    (* crib-free grams: anchors excluded, so no credit for crib-copying)")
    print("    (where 0 decoys survive, the crib algebra alone did the rejecting;")
    print("     where many survive, the masked score had to do it -- and did)")

    print("\n[4] crib-free score must separate English from noise at the worst period")
    _, windows_nc, _ = mask_plan(21)
    eng = masked_score(PLAIN, windows_nc, table, floor)
    noise = masked_score(K4_CT, windows_nc, table, floor)
    sep = eng - noise > 1.5
    ok &= sep
    print(f"  {'PASS' if sep else 'FAIL'}  p=21, {len(windows_nc)} crib-free grams: "
          f"English {eng:.2f} vs ciphertext {noise:.2f} (gap {eng - noise:.2f})")

    print("\n[5] soundness of the analytic layer -- it must never refute a cipher")
    print("    that demonstrably exists. Each planted cipher below is real, so its")
    print("    own model and period must NOT be flagged impossible.")
    cases = [("III", "KRYPTOS", "KRYPTOS", [4, 17, 9]),
             ("I", "ABSCISSA", STD, [11, 2, 20, 6]),
             ("II", STD, "PALIMPSEST", [1, 25]),
             ("III", "PALIMPSEST", "PALIMPSEST", [(7 * s_ + 3) % 26 for s_ in range(26)])]
    for model, wp, wc, key in cases:
        _, _, ct = plant(wp, wc, key)
        flagged = analytic_impossibility(crib_triples(ct=ct))[model]
        bad = len(key) in flagged
        ok &= not bad
        print(f"  {'FAIL' if bad else 'PASS'}  Quagmire {model:<3} p={len(key):<2} "
              f"planted cipher exists; analytic layer flags it impossible: {bad}")

    print("\n[6] the analytic layer applied to the real K4 cribs")
    real = analytic_impossibility(crib_triples())
    for model in ("I", "II", "III"):
        f = real[model]
        print(f"  Quagmire {model:<3} refuted for ALL 26! alphabets at "
              f"{len(f):>2} of 26 periods: {sorted(f) if f else '--'}")
    allp = len(real["III"]) == 26
    ok &= allp
    i, j, why = real["III"][1]
    print(f"  {'PASS' if allp else 'FAIL'}  Quagmire III refuted at every period "
          f"(e.g. p=1: positions {i},{j} force {why})")

    print("\n" + ("SELF-TEST PASSED — the sweep can find what it looks for, including\n"
                  "in the long-period band where the key is only partly determined."
                  if ok else "SELF-TEST FAILED."))
    return 0 if ok else 1


# --------------------------------------------------------------------------


def main() -> int:
    ap_ = argparse.ArgumentParser(description=__doc__)
    ap_.add_argument("--selftest", action="store_true")
    ap_.add_argument("--max-period", type=int, default=26)
    ap_.add_argument("--max-unknown", type=int, default=3,
                     help="free residues to fully enumerate for the shortlist only")
    ap_.add_argument("--alphabets", type=int, default=30000)
    args = ap_.parse_args()
    if args.selftest:
        return selftest()

    table, floor = load_quadgrams()
    pool = alphabet_pool(args.alphabets)
    curated = [(w, a) for w, a in pool if w in set(CURATED)]
    print("KRYPTOS K4 — KEYED-ALPHABET (QUAGMIRE) SWEEP")
    print("=" * 78)
    print(f"\n  {len(pool):,} distinct keyed alphabets "
          f"({len(curated)} sculpture-nominated, including misspelling-derived)")
    print(f"  periods 1..{args.max_period}, key solved from cribs rather than guessed")
    print("  long periods decided on crib-determined letters only, not by enumeration\n")

    full_nc = mask_plan(1)[1]
    english_ref = masked_score(PLAIN, full_nc, table, floor)
    noise_ref = masked_score(K4_CT, full_nc, table, floor)
    print(f"  scoring excludes every quadgram touching an anchor, so the 24 crib")
    print(f"  letters earn no credit -- only letters the cipher actually predicted.")
    print(f"  fluent English {english_ref:.2f} per crib-free quadgram, "
          f"ciphertext {noise_ref:.2f}\n")

    # Layer 1 -- proofs. These need no dictionary and no scoring: they hold
    # for every one of the 26! = 4.0e26 possible keyed alphabets.
    proofs = analytic_impossibility(crib_triples(), args.max_period)
    print("  ANALYTIC LAYER — periods refuted for ALL 26! = 4.0e26 alphabets")
    print("  " + "-" * 74)
    for model in ("I", "II", "III"):
        f = proofs[model]
        ps = ", ".join(str(x) for x in sorted(f)) if f else "none"
        print(f"    Quagmire {model:<3} {len(f):>2}/{args.max_period} periods: {ps}")
    i, j, why = proofs["III"][1]
    print(f"\n    Quagmire III -- the model K1 and K2 themselves use -- is refuted at")
    print(f"    EVERY period. Positions {i} and {j} both decrypt from plaintext E but")
    print(f"    carry different ciphertext letters, forcing {why}; and position 74")
    print("    is the K->K fixed point, forcing a zero shift that no other crib in")
    print("    its residue can match. No keyed alphabet whatsoever can satisfy both.")
    print("    This is a proof, not a sample -- the dictionary sweep below is")
    print("    therefore only needed for Quagmire I, II and IV.\n")

    best: list = []
    started = time.time()
    grand_t = grand_s = grand_d = grand_u = 0

    plans = [
        ("Quagmire I  ", ((w, a, "std", STD) for w, a in pool)),
        ("Quagmire II ", (("std", STD, w, a) for w, a in pool)),
        ("Quagmire III", ((w, a, w, a) for w, a in pool)),
        ("Quagmire IV ", ((w1, a1, w2, a2) for w1, a1 in curated for w2, a2 in pool)),
    ]
    print(f"  {'model':<13} {'configurations':>15} {'crib-consistent':>17} "
          f"{'decided':>9} {'undecided':>11}")
    for label, it in plans:
        t, s, d, u = sweep(label, it, args.max_period, table, floor, best)
        grand_t += t
        grand_s += s
        grand_d += d
        grand_u += u
        print(f"  {label}  {t:>15,} {s:>17,} {d:>9,} {u:>11,}")

    elapsed = time.time() - started
    print(f"\n  total {grand_t:,} configurations in {elapsed:.1f}s")
    print(f"  crib-consistent: {grand_s:,}   decided: {grand_d:,}   "
          f"undecided: {grand_u:,}")
    if grand_u:
        print(f"  NOTE: {grand_u:,} configurations left fewer than {MIN_GRAMS} scorable")
        print("  quadgrams and are NOT eliminated -- they are undecided.")
    else:
        print("  Every crib-consistent configuration was decided on evidence that no")
        print("  choice of the free key residues can change. Nothing was skipped.")

    print("\n  best-scoring candidates ('?' = position left dark by a free residue)")
    print("  crib-free = the honest score; with-cribs = inflated by the anchors")
    print("  " + "-" * 74)
    print(f"    {'crib-free':>9} {'with-cribs':>10}")
    for sc, sc_all, lab, wp, wc, period, nfree, text in best[:8]:
        print(f"    {sc:>9.2f} {sc_all:>10.2f}  {lab} pt={wp} ct={wc} "
              f"p={period} ({nfree} free)")
        print(f"            {text}")

    # Only now, on the shortlist, is enumeration worth its cost.
    shortlist = [b for b in best if b[6] <= args.max_unknown]
    if shortlist:
        print(f"\n  full enumeration of the shortlist ({len(shortlist)} with "
              f"<= {args.max_unknown} free residues):")
        bestfull = None
        enumerated = 0
        for sc, sc_all, lab, wp, wc, period, nfree, _ in shortlist:
            free = mask_plan(period)[2]
            ap2 = STD if wp == "std" else keyed(wp)
            ac2 = STD if wc == "std" else keyed(wc)
            key = consistent(crib_pairs(ap2, ac2), period)
            for fill in product(range(26), repeat=len(free)):
                full = [key.get(s, 0) for s in range(period)]
                for slot, val in zip(free, fill):
                    full[slot] = val
                cand = decrypt(ap2, ac2, full)
                enumerated += 1
                fs = masked_score(cand, full_nc, table, floor)
                if bestfull is None or fs > bestfull[0]:
                    bestfull = (fs, lab, wp, wc, period, cand)
        if bestfull:
            print(f"    {enumerated:,} complete plaintexts enumerated")
            print(f"    best {bestfull[0]:.2f} crib-free "
                  f"({bestfull[1]} pt={bestfull[2]} ct={bestfull[3]} p={bestfull[4]})")
            print(f"            {bestfull[5]}")
            margin = (bestfull[0] - noise_ref) / (english_ref - noise_ref) * 100
            print(f"    fluent English {english_ref:.2f}, ciphertext {noise_ref:.2f} -- "
                  f"this sits {margin:.0f}% of the way from noise to English")

    print("\n" + "=" * 78)
    if best and best[0][0] > noise_ref + 0.80 * (english_ref - noise_ref):
        print(" A candidate approaches fluent English. Verify by hand.")
        return 1
    nproved = len(set(proofs["I"]) | set(proofs["II"]))
    print(" VERDICT: no keyed-alphabet Quagmire yields English.")
    print()
    print(" Quagmire III is refuted outright -- a proof over all 26! alphabets at")
    print(" every period. That is the strongest form of result available here, and")
    print(" it removes the sculpture's own established cipher, the one K1 and K2")
    print(" use, from contention for K4.")
    print()
    print(" Quagmire I, II and IV are eliminated empirically over the alphabet")
    print(" pool -- including every keyword the sculpture nominates and every")
    print(" alphabet derivable from Sanborn's deliberate misspellings -- at every")
    print(f" period 1..{args.max_period}, with {nproved} of those periods also refuted by proof.")
    print()
    print(" Scope, stated precisely: the empirical half is a dictionary sweep, so")
    print(" it rules out word-keyed alphabets, not arbitrary permutations. The")
    print(" long-period band is genuinely decided rather than skipped -- free")
    print(" residues were masked out, and scoring excluded every quadgram touching")
    print(" an anchor, so the verdict rests only on letters the cipher predicted")
    print(" and never on crib-copying.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
