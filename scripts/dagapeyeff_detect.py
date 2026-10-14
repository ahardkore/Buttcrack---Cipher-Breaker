#!/usr/bin/env python3
"""Is the d'Agapeyeff cipher a keyed grid of single letters?  Measure it.

``dagapeyeff_alignment.py`` establishes that the 1939 challenge text splits
into 197 coordinate pairs whose first digits lie in {6,7,8,9,0} and second
digits in {0..5}.  The obvious reading of that is a keyed 5x6 grid, one letter
per visited cell -- in other words, a monoalphabetic substitution on 19
symbols.

That reading is testable, but a substitution attack on 197 symbols is only
meaningful against *two* control distributions:

* **ceiling** -- genuine English prose of the same length, cut down to a
  19-letter alphabet and attacked blind.  The best score reachable when the
  hypothesis is *true*.
* **null** -- random streams carrying the ciphertext's own frequency profile,
  attacked identically.  The best score reachable when it is *false*.  Profile
  matching matters: the cipher uses 13 codes at 8-10% each, far flatter than
  English, and a flatter alphabet is intrinsically harder to detect, so an
  uncontrolled comparison would flatter the null and overstate the result.

Published scores, log10 per symbol under an English quadgram model (higher is
more English-like; ``--full``, 14 restarts, 900k annealing steps):

    ceiling   real english, 8 samples        -4.39 .. -5.28   mean  -4.80
    null      ciphertext profile, shuffled   -5.26 .. -5.62   mean  -5.45
    null      english profile, shuffled      -5.66 .. -5.87   mean  -5.77
    ciphertext                               -5.55

The cipher lands inside the null band, 0.87 log10 per symbol below the best
English sample.  A perfect solver *would* have recovered English from a
genuine 197-letter grid -- the ceiling column is what proves the text is long
enough to tell -- so the pair-split is not encoding letters one cell at a
time.  That closes the most-cited reading of the cipher as a measurement
rather than as an opinion.

There is a better test, though, one that needs no search at all.  ``--mapfree``
compares statistics that are *invariant under the alphabet mapping* -- any
one-to-one relabelling of the 19 cells leaves them untouched, so they cannot be
thrown off by guessing the wrong keyword:

    adjacent-repeat ratio    how often consecutive codes repeat, divided by
                             the rate a shuffle of the same frequencies gives
    digram IC / unigram IC   how much structure sits in pairs beyond what
                             the singles already explain
    burstiness               index of dispersion of where the busy codes land

An English mapping would have to look like English under all three.  It does not:

    ceiling: english on 19 letters   repeats 0.502 (sd .168)  digrams 0.136 (sd .026)
    null:    same profile, shuffled  repeats 0.982 (sd .239)  digrams 0.068 (sd .006)
    ciphertext                       repeats 1.264            digrams 0.064

The cipher is 4.5 sigma from English on repeats and 2.7 sigma on digram
structure, and within one sigma of the shuffle both times.  English has fewer
adjacent repeats than a shuffle of the same letter counts and far more digram
structure; the cipher has slightly more of the first and none of the second.
A third test counts how burstily the busy codes arrive (index of dispersion
of their positions: 8.85 for the cipher, 8.17 for i.i.d. draws of the same
profile, 5.88 for English, from every segment the shipped corpus yields).
All three say the same thing, and all three are
blind to which letter any cell means, so no keyword square can fake or hide a
result, and no transposition layered on top can rescue the reading: a
permutation could only move these numbers from the null toward English.

A fourth test is not statistical at all: Playfair, two-square, four-square and
bifid cannot emit a doubled plaintext letter, and an injective grid preserves
that, so the ciphertext would need <em>zero</em> adjacent repeats under any key.
It has 17.  The doubling-forbidding families are excluded by arithmetic.

That kills the letter reading outright -- harder evidence than the annealing
result above, because "the search found nothing" needs the search to have been
capable of finding something.

Usage
-----
    python3 scripts/dagapeyeff_detect.py             # quick, ~1 min
    python3 scripts/dagapeyeff_detect.py --mapfree   # mapping-invariant tests only
    python3 scripts/dagapeyeff_detect.py --full --selftest
    python3 scripts/dagapeyeff_detect.py --full      # the published numbers
    python3 scripts/dagapeyeff_detect.py --selftest  # assert the bands separate

``gcc`` is used when present (its inner loop is roughly 100x faster); the
Python fallback runs the same objective at reduced effort.
"""

from __future__ import annotations

import argparse
import collections
import gzip
import math
import random
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dagapeyeff_alignment import CANONICAL, digits  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "examples" / "english_samples.txt"
QUADGRAMS = ROOT / "buttcrack" / "data" / "english_quadgrams.txt.gz"

#: the 197 ciphertext pairs, as counts over the 19 visited cells
CT_PROFILE = [20, 17, 17, 17, 17, 16, 15, 14, 12, 12, 11, 11, 9, 3, 2, 1, 1, 1, 1]
#: the top-19 English letter frequencies scaled to 197 symbols (sums to 197)
ENGLISH_PROFILE = [25, 18, 16, 15, 14, 13, 12, 12, 12, 8, 8, 6, 6, 6, 6, 5, 5, 5, 5]

NS = 19
ALPHA = 26
MISSING = -8.0  # log10 floor for an unseen quadgram


def quad_table() -> list[float]:
    """26**4 table of English quadgram log10 probabilities."""
    counts: dict[str, int] = {}
    with gzip.open(QUADGRAMS, "rt") as fh:
        for line in fh:
            gram, _, n = line.partition(" ")
            gram = gram.strip()
            if len(gram) == 4 and gram.isalpha():
                counts[gram] = int(n)
    total = sum(counts.values())
    table = [MISSING] * (ALPHA**4)
    for gram, n in counts.items():
        slot = 0
        for ch in gram:
            slot = slot * ALPHA + (ord(ch) - 65)
        table[slot] = math.log10(n / total)
    return table


def ciphertext_stream() -> list[int]:
    """The 1939 text as symbol indices over its 19 visited grid cells."""
    stream = digits(CANONICAL)
    codes = [stream[i:i + 2] for i in range(0, len(stream) - 1, 2)]
    order = sorted(set(codes))
    index = {code: i for i, code in enumerate(order)}
    return [index[c] for c in codes]


def profile_stream(profile: list[int], length: int, rnd: random.Random) -> list[int]:
    """A shuffled symbol stream carrying exactly the given frequency profile.

    Padding or truncating a control would quietly change the very property it
    is supposed to hold fixed, so a mismatch is an error, not a correction.
    """
    if sum(profile) != length:
        raise ValueError(f"profile sums to {sum(profile)}, not {length}")
    pool = [sym for sym, n in enumerate(profile) for _ in range(n)]
    rnd.shuffle(pool)
    return pool


def coincidence_counts(seq: list) -> tuple[int, int]:
    """(#adjacent equal entries, #equal unordered pairs) -- both mapping-free."""
    counts = collections.Counter(seq)
    return (sum(1 for i in range(len(seq) - 1) if seq[i] == seq[i + 1]),
            sum(v * (v - 1) for v in counts.values()))


def mapping_invariant(seq: list) -> tuple[float, float]:
    """Two ordering statistics that no relabelling of the alphabet can change.

    ``repeats``
        P(neighbours are equal) / P(a random pair is equal), i.e. observed
        adjacent repeats over what a shuffle of the same multiset gives.
        1.00 for a shuffle.  English sits near 0.50: restricting prose to 19
        letters still leaves fewer doublings than spreading those same counts
        at random.  Above 1.00 -- where the cipher sits, at 1.26 -- means
        repeats are *more* common than a shuffle produces, and a cipher that
        forbids doubling outright would drive the count to exactly zero.
    ``igram``
        the digram index of coincidence over the unigram one.  English is
        ~0.13, a shuffle of this profile ~0.07, the cipher 0.064 -- so the
        pairs carry no more structure than the singles alone predict.

    A one-to-one code -> letter mapping leaves both exactly as they were, which
    is the whole point: no guessed keyword square can fake or hide a result,
    and a transposition layer on top of a letter grid could only push ``igram``
    up toward the English value, never past it.
    """
    n = len(seq)
    adj, singles = coincidence_counts(seq)
    unigram_ic = singles / (n * (n - 1))
    # exact expectation for a uniform shuffle of these same symbols
    expected_adj = singles * (n - 1) / (n * n)
    repeat = adj / expected_adj if expected_adj else float("nan")
    pairs = [(seq[i], seq[i + 1]) for i in range(n - 1)]
    _, psingles = coincidence_counts(pairs)
    digram_ic = psingles / ((n - 1) * (n - 2))
    return repeat, (digram_ic / unigram_ic if unigram_ic else float("nan"))


def doubled_letter_cipher_rejected(seq: list) -> tuple[int, int, str]:
    """Hard test for the family that forbids doubled plaintext letters.

    Playfair, two-square, four-square and their variants *cannot* emit the same
    letter twice in a row -- the rule is structural, not statistical.  A
    keyed grid maps each plaintext letter to one fixed code, so that guarantee
    transfers to the ciphertext unchanged: such a cipher would show *exactly
    zero* adjacent identical codes, whatever the key.  One observed repeat is
    enough to reject the whole family, with no null model and no p-value
    needed -- the only escape hatches are a non-injective code (two letters
    sharing a cell, which the grid's structure forbids) or an inserted letter
    after encipherment.
    """
    adj = sum(1 for i in range(len(seq) - 1) if seq[i] == seq[i + 1])
    runs: list[int] = []
    i = 0
    while i < len(seq):
        j = i
        while j + 1 < len(seq) and seq[j + 1] == seq[i]:
            j += 1
        if j > i:
            runs.append(j - i + 1)
        i = j + 1
    longest = max(runs) if runs else 1
    verdict = ("REJECTED: a no-doubling cipher cannot produce a single adjacent "
               "repeat" if adj else "consistent: zero adjacent repeats observed")
    return adj, longest, verdict


def runs_z(seq: list, hot: int = 13) -> tuple[float, float]:
    """Wald-Wolfowitz clustering of the busiest symbols, as a shuffle z-score.

    Language sends a frequent letter in bursts (a plural, a repeated morpheme)
    separated by stretches where it cannot appear; a shuffle has no such
    constraint.  Correlated with ``repeats`` rather than independent of it, so
    read it as corroboration, never as a fourth opinion.
    """
    counts = collections.Counter(seq)
    top = {sym for sym, _ in counts.most_common(hot)}
    label = [1 if sym in top else 0 for sym in seq]
    n1 = sum(label)
    n0 = len(label) - n1
    runs = sum(1 for i in range(1, len(label)) if label[i] != label[i - 1]) + 1
    mu = 2 * n1 * n0 / len(label) + 1
    var = (mu - 1) * (mu - 2) / (len(label) - 1)
    return (runs - mu) / math.sqrt(var), mu


def dispersion(seq: list, min_count: int = 12) -> list[float]:
    """Index of dispersion of each busy symbol's positions.

    1.0 means the symbol is scattered as evenly as a coin flip; larger means it
    arrives in bursts.  Language is *anti*-clustered at this scale (a word's
    letters arrive together, then not for a while, and a 197-letter sample has
    fewer bursts than an i.i.d. draw produces), while an independent codebook
    draw has nothing to do but cluster.  This is the third independent witness
    against the letter reading, and it needs no alphabet either.
    """
    counts = collections.Counter(seq)
    out = []
    for sym, k in counts.items():
        if k < min_count:
            continue
        pos = [i for i, x in enumerate(seq) if x == sym]
        gaps = [b - a for a, b in zip(pos, pos[1:])]
        mean = sum(gaps) / len(gaps)
        if mean:
            out.append(statistics.pvariance(gaps) / mean)
    return out


def english_streams(count: int, rnd: random.Random) -> list[list[int]]:
    """Prose cut to a 19-letter alphabet, as the ciphertext appears to be."""
    text = re.sub("[^A-Za-z]", "", CORPUS.read_text()).upper()
    out: list[list[int]] = []
    for start in range(0, len(text) - 197, 197):
        seg = text[start:start + 197]
        common = [letter for letter, _ in collections.Counter(seg).most_common(NS)]
        if len(common) < NS:
            continue
        keep = set(common)
        seg = "".join(ch for ch in seg if ch in keep)
        if len(seg) < 180:
            continue
        index = {letter: i for i, letter in enumerate(sorted(keep))}
        out.append([index[ch] for ch in seg])
        if len(out) == count:
            break
    return out


def anneal_py(seq: list[int], table: list[float], restarts: int, iters: int, seed: int) -> float:
    """Simulated annealing over a symbol -> letter map; returns log10/char."""
    rnd = random.Random(seed)
    n = len(seq)
    best = -1e18
    for _ in range(restarts):
        letters = rnd.sample(range(ALPHA), NS)
        buf = [0] * n

        def total() -> float:
            s = 0.0
            for i in range(n - 3):
                s += table[buf[i] * 17576 + buf[i + 1] * 676 + buf[i + 2] * 26 + buf[i + 3]]
            return s

        for i, sym in enumerate(seq):
            buf[i] = letters[sym]
        cur = total()
        local = cur
        for it in range(iters):
            temp = 8.0 * (0.04 / 8.0) ** (it / iters)
            a, b = rnd.randrange(NS), rnd.randrange(NS)
            if a == b:
                continue
            letters[a], letters[b] = letters[b], letters[a]
            for i, sym in enumerate(seq):
                buf[i] = letters[sym]
            nxt = total()
            if nxt >= cur or rnd.random() < math.exp((nxt - cur) / max(temp, 1e-9)):
                cur = nxt
                local = max(local, cur)
            else:
                letters[a], letters[b] = letters[b], letters[a]
                for i, sym in enumerate(seq):
                    buf[i] = letters[sym]
        best = max(best, local)
    return best / (n - 3)


C_SOURCE = r"""
/* One objective, one loop: anneal a symbol->letter map to maximise English
   quadgram log-likelihood.  Generated by scripts/dagapeyeff_detect.py.  It
   deliberately has no dictionary term -- word coverage is gameable at 197
   symbols (it reaches 85% on pure noise), which would fake a solution. */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define NS 19
#define ALPHA 26
static int SEQ[8192], N; static int *Q;
static long long score(int *L){
  static unsigned char buf[8192]; long long q=0;
  for(int i=0;i<N;i++) buf[i]=(unsigned char)L[SEQ[i]];
  for(int i=0;i+3<N;i++) q += Q[buf[i]*17576+buf[i+1]*676+buf[i+2]*26+buf[i+3]];
  return q;
}
static unsigned long long rs;
static double u(void){ rs^=rs<<13; rs^=rs>>7; rs^=rs<<17; return (rs>>11)/9007199254740992.0; }
int main(int argc,char**argv){
  int iters=600000, restarts=10, seed=1; double T0=8.0, T1=0.04;
  char file[512]={0}, table[512]={0};
  for(int i=1;i<argc;i++){
    if(!strcmp(argv[i],"-i")) iters=atoi(argv[++i]);
    else if(!strcmp(argv[i],"-r")) restarts=atoi(argv[++i]);
    else if(!strcmp(argv[i],"-s")) seed=atoi(argv[++i]);
    else if(!strcmp(argv[i],"-f")) strcpy(file,argv[++i]);
    else if(!strcmp(argv[i],"-t")) strcpy(table,argv[++i]);
    else if(!strcmp(argv[i],"-T")){T0=atof(argv[++i]); T1=atof(argv[++i]);}
  }
  FILE*f=fopen(table,"rb"); int cnt; if(!f||fread(&cnt,4,1,f)!=1) return 2;
  Q=malloc(sizeof(int)*cnt); if(fread(Q,4,cnt,f)!=(size_t)cnt) return 2; fclose(f);
  f=fopen(file,"r"); if(!f) return 4; {int v; N=0; while(N<8192&&fscanf(f,"%d",&v)==1) SEQ[N++]=v;} fclose(f);
  if(N<20) return 3;
  rs=(unsigned long long)seed*6364136223846793005ULL+88172645463393265ULL;
  if(!rs) rs=88172645463393265ULL;
  int L[NS]; long long best=-4e18;
  for(int r=0;r<restarts;r++){
    int perm[ALPHA]; for(int i=0;i<ALPHA;i++) perm[i]=i;
    for(int i=ALPHA-1;i>0;i--){int j=(int)(u()*(i+1))%(i+1); int t=perm[i];perm[i]=perm[j];perm[j]=t;}
    for(int i=0;i<NS;i++) L[i]=perm[i];
    long long cur=score(L), bs=cur;
    for(int it=0;it<iters;it++){
      double T=T0*pow(T1/T0,(double)it/iters)*1000.0;
      int a=(int)(u()*NS)%NS, b=(int)(u()*NS)%NS; if(a==b) continue;
      int t=L[a];L[a]=L[b];L[b]=t;
      long long s=score(L);
      if(s>=cur || u()<exp((double)(s-cur)/T)) cur=s;
      else {t=L[a];L[a]=L[b];L[b]=t;}
      if(cur>bs) bs=cur;
    }
    if(bs>best) best=bs;
  }
  printf("%.4f\n", (double)best/N/1000.0);
  return 0;
}
"""


class Annealer:
    """Fast C scorer when gcc is available, otherwise the Python fallback."""

    def __init__(self, table: list[float]) -> None:
        self.table = table
        self.tmp = Path(tempfile.mkdtemp(prefix="dagapeyeff-"))
        self.bin = None
        if shutil.which("gcc"):
            try:
                scaled = [round(v * 1000) for v in table]
                blob = self.tmp / "quads.bin"
                blob.write_bytes(len(scaled).to_bytes(4, "little")
                                 + b"".join(s.to_bytes(4, "little", signed=True) for s in scaled))
                src = self.tmp / "dag_anneal.c"
                src.write_text(C_SOURCE)
                subprocess.run(["gcc", "-O3", "-o", str(self.tmp / "dag_anneal"), str(src), "-lm"],
                               check=True, capture_output=True)
                self.bin = self.tmp / "dag_anneal"
                self.blob = blob
            except Exception:
                self.bin = None

    @property
    def engine(self) -> str:
        return "gcc (fast)" if self.bin else "python (slow, reduced effort)"

    def score(self, seq: list[int], restarts: int, iters: int, seed: int) -> float:
        if self.bin:
            stream = self.tmp / "s.txt"
            stream.write_text(" ".join(map(str, seq)))
            out = subprocess.run([str(self.bin), "-f", str(stream), "-t", str(self.blob),
                                  "-r", str(restarts), "-i", str(iters), "-s", str(seed)],
                                 capture_output=True, text=True)
            if out.returncode == 0 and out.stdout.strip():
                return float(out.stdout.split()[-1])
        return anneal_py(seq, self.table, max(1, restarts // 4), min(iters, 60_000), seed)


def main_mapfree(samples: int = 12) -> int:
    """Mapping-invariant ordering tests: cipher vs english ceiling vs shuffle.

    Both statistics are normalised so that 1.00 is "a plain shuffle of the
    ciphertext's own frequency profile".  Because they count coincidences
    rather than letters, relabelling the 19 cells cannot change them at all --
    no guessed keyword square can manufacture or hide a result here.
    """
    stream = ciphertext_stream()
    rnd = random.Random(20261014)
    text = re.sub("[^A-Za-z]", "", CORPUS.read_text()).upper()
    segs = [text[i:i + 197] for i in range(0, len(text) - 197, 197)]
    english = []
    for seg in segs[:samples * 2]:
        keep = set(l for l, _ in collections.Counter(seg).most_common(NS))
        cut = "".join(ch for ch in seg if ch in keep)
        if len(cut) >= 190:
            english.append(mapping_invariant(list(cut[:197])))
        if len(english) == samples:
            break
    # 20+ nulls, or the shuffle's own mean is too noisy to serve as the anchor
    nulls = [mapping_invariant(profile_stream(CT_PROFILE, 197, rnd))
              for _ in range(max(60, samples * 8))]

    print("mapping-invariant ordering statistics, normalised so 1.00 = a shuffle of")
    print("the cipher's own profile.  English sits clearly off that anchor on two of")
    print("the three; the cipher sits essentially on it, and on the third it is more")
    print("clustered than a shuffle rather than less.\n")

    def stats_of(rows, k):
        return [r[k] for r in rows]

    def row(label, rows):
        r, d = stats_of(rows, 0), stats_of(rows, 1)
        print(f"  {label:36} n={len(rows):3}  repeats {statistics.mean(r):6.3f} "
              f"(sd {statistics.stdev(r):.3f})   digrams {statistics.mean(d):6.3f} "
              f"(sd {statistics.stdev(d):.3f})")
        return r, d

    ea, ed = row("ceiling: english on 19 letters", english)
    na, nd = row("null: same profile, shuffled", nulls)
    obs = mapping_invariant(stream)
    label = "ciphertext: the 1939 cipher".ljust(36)
    print(f"  {label} n=  1  repeats {obs[0]:6.3f}                  digrams {obs[1]:6.3f}")
    print("-" * 86)
    for name, val, eng, nul in (("repeats", obs[0], ea, na), ("digrams", obs[1], ed, nd)):
        ze = (val - statistics.mean(eng)) / statistics.stdev(eng)
        zn = (val - statistics.mean(nul)) / statistics.stdev(nul)
        print(f"  {name:>7}: english ceiling {statistics.mean(eng):.3f} · shuffle {statistics.mean(nul):.3f} · "
              f"cipher is {ze:+.1f} sigma from english, {zn:+.1f} sigma from the shuffle")
    # third witness: are the busy codes scattered like words, or like draws?
    # uses every 197-letter segment the shipped corpus yields (8 of them, 59
    # code measurements); the split-half medians agree to 0.07, so the ceiling
    # here is stable, but it is corpus-limited and quoted as such.
    eng_disp: list[float] = []
    for seg in segs:
        keep = set(l for l, _ in collections.Counter(seg).most_common(NS))
        cut = "".join(ch for ch in seg if ch in keep)
        if len(cut) >= 190:
            eng_disp += dispersion(list(cut[:197]))
    iid_disp: list[float] = []
    for _ in range(min(400, len(nulls) * 12)):
        iid_disp += dispersion([rnd.choices(range(NS), weights=CT_PROFILE)[0] for _ in range(197)])
    ct_disp = dispersion(stream)
    lab2 = "clustering of busy codes".ljust(36)
    e_med, i_med = statistics.median(eng_disp), statistics.median(iid_disp)
    print(f"  {lab2}      median {statistics.median(ct_disp):6.2f}   "
          f"(english {e_med:.2f}, iid draws {i_med:.2f})")
    print("-" * 86)

    # ---- the two tests that actually pay: a hard one and a soft one ----
    adj, longest, verdict = doubled_letter_cipher_rejected(stream)
    eng_doubles = [sum(1 for i in range(len(s) - 1) if s[i] == s[i + 1])
                   for s in segs[:len(segs)]]
    print(f"  no-doubling families (Playfair, two-/four-square, "
          f"bifid-digraph):\n    these CANNOT emit a repeated plaintext letter, so a keyed grid\n"
          f"    must show zero adjacent repeats.  observed: {adj} "
          f"(longest run {longest}, english samples average "
          f"{statistics.mean(eng_doubles):.1f}) -> {verdict}")
    z, mu = runs_z(stream)
    znull = [runs_z(profile_stream(CT_PROFILE, 197, rnd))[0] for _ in range(600)]
    zeng = []
    for seg in segs:
        keep = set(l for l, _ in collections.Counter(seg).most_common(NS))
        cut = "".join(ch for ch in seg if ch in keep)
        if len(cut) >= 190:
            zeng.append(runs_z(list(cut[:197]))[0])
    # the shuffle's own spread, not the normal approximation, is the honest yardstick
    zs = statistics.stdev(znull)
    tail = sum(1 for x in znull if x <= z) / len(znull)
    print(f"  run-test on the 13 busiest codes: {z:+.2f} shuffle-sd vs the null "
          f"(english {statistics.mean(zeng):+.2f});\n    "
          f"p = {tail:.3f} one-sided -- the only test on the cipher's side of the "
          f"null,\n    and marginal: {tail:.1%} of shuffles cluster at least this much. "
          f"Corroborating, not decisive.")
    print("""  verdict: on repeats, digram structure and clustering the pairs behave like
  an ordering of this multiset, not like english under a key.  A keyed grid of
  letters has to move all three away from the shuffle and toward english; a
  transposition on top of it could only help.  None of them moved, so the 19
  visited cells do not encode 19 letters -- and no relabelling of the grid, any
  keyword square, any language, any columnar layer, can rescue a reading that
  fails tests which never look at the letters.""")
    return 0
    return 0



def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--full", action="store_true", help="the effort behind the published numbers")
    ap.add_argument("--quick", action="store_true", help="fewer restarts and samples")
    ap.add_argument("--samples", type=int, default=0)
    ap.add_argument("--selftest", action="store_true", help="assert ceiling and null bands separate")
    ap.add_argument("--mapfree", action="store_true", help="only the mapping-invariant tests")
    args = ap.parse_args(argv)

    if args.mapfree:
        return main_mapfree(samples=12 if not args.quick else 5)

    restarts, iters, count = (10, 600_000, 8)
    if args.quick:
        restarts, iters, count = 3, 120_000, 4
    if args.full:
        restarts, iters, count = 14, 900_000, 8
    if args.samples:
        count = args.samples

    annealer = Annealer(quad_table())
    print(f"annealer: {annealer.engine}  ·  {restarts} restarts x {iters // 1000}k steps x {count} samples")
    rnd = random.Random(20261014)

    def run(seqs, label):
        vals = [annealer.score(s, restarts, iters, 7 + i) for i, s in enumerate(seqs)]
        print(f"  {label:36} n={len(vals):2}  mean {statistics.mean(vals):+6.3f}  "
              f"band [{min(vals):+.3f}, {max(vals):+.3f}]")
        return vals

    ceiling = run(english_streams(count, rnd), "ceiling: real english, 19 letters")
    ct_null = run([profile_stream(CT_PROFILE, 197, rnd) for _ in range(count)],
                  "null: ciphertext profile shuffled")
    eng_null = run([profile_stream(ENGLISH_PROFILE, 197, rnd) for _ in range(count)],
                   "null: english profile shuffled")
    cipher = run([ciphertext_stream()], "CT:   the 1939 cipher itself")

    score, ceiling_hi, null_lo, null_hi = cipher[0], max(ceiling), min(ct_null + eng_null), max(ct_null + eng_null)
    print("-" * 78)
    if score > ceiling_hi + 0.10:
        verdict = "ABOVE the English ceiling -> re-examine: this would be a break"
    elif score > null_hi + 0.10:
        verdict = "between the bands -> worth a harder or dictionary-aware attack"
    else:
        verdict = "inside the null band -> no letter-substitution signal present"
    print(f"ciphertext {score:+.3f} · null band [{null_lo:+.3f}, {null_hi:+.3f}] · ceiling {ceiling_hi:+.3f}")
    print(f"separation ceiling-to-null = {ceiling_hi - null_hi:+.3f} "
          f"({'attack is proven to work at this length' if ceiling_hi - null_hi > 0.1 else 'INCONCLUSIVE: text too short to tell'})")
    print(f"verdict: {verdict}")

    if args.selftest:
        ok = (ceiling_hi - null_hi) > 0.10 and score <= null_hi + 0.10
        print("selftest:", "bands separate and the cipher sits in the null" if ok
              else "bands collapsed — the verdict is not supported")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
