# PK9 Session Report — Ground-Truth Corrections & Word-Wheel Sweep Campaign

**Date**: 2026-10-02
**Scope**: PK9 (N = 144, `KSYAWFEYYOIS…KAMHIJXD`), the last unsolved Paradigm
Kryptos challenges together with PK10.
**Headline**: The repository's ground-truth records for **PK4, PK5 and PK7 were
wrong**; they are now corrected and every PK1–PK8 construction is reproduced
exactly from independently verified conventions.  A new exhaustive
wheel-word × transposition sweep engine was built and validated; the staged
campaign it is running has so far produced only negative results.

---

## 1. Ground-truth corrections (PK4, PK5, PK7)

The public reference implementation [TTFH/KRYPTOS](https://github.com/TTFH/KRYPTOS)
(commit `3d60736`, extended through `73091e4`) contains round-trip-verified
constructions for PK1–PK8.  `verify_pk_constructions.py` (new) re-implements
every construction from scratch in Python and confirms **all eight official
ciphertexts are reproduced exactly**.

The repository's previously recorded plaintexts for PK4, PK5 and PK7 —
"The strings measure two furlongs…", "We examined the fibers under the lens…",
"He pointed to the hearth…" — **do not encrypt to the official ciphertexts
under any convention** and are early-session fabrications.  They have been
replaced in `pk_verified_solutions.json`, `pk_submission_manifest.json` and
`kryptos-app/data.js` (whose PK4/PK5/PK7 ciphertext fields were also corrupted
by block repetition) by the verified texts:

| Puzzle | Construction (encryption order) | Keys | Plaintext opens |
| :--- | :--- | :--- | :--- |
| PK1 | Q(10) | `PROVENANCE` | "Investigation log, item eight: knot…" *(unchanged)* |
| PK2 | T(7) | `MARGINS` | "I have found references to the knot…" *(unchanged)* |
| PK3 | Q(8)Q(10) | `ORDINATE`, `PENTIMENTO` | "Seventh month…" *(unchanged)* |
| **PK4** | **T(8) Q(5) Q(9)** | **`UNDERLAY`, `OCHRE`, `VERDIGRIS`** | "Two years in. The needle's trail led me to a craftsman named the Whitesmith…" |
| **PK5** | **T(8) Q(224)** | **`TWOYEARS`, + the entire PK4 plaintext as the 224-letter Quagmire key** | "Fourteen days in the barn…" |
| PK6 | T(9)T(9)Q(6) | `HANDIWORK`, `SMITHWORK`, `PORTAL` | "The Whitesmith's workshop…" *(plaintext was already correct)* |
| **PK7** | **Q(6) + Hill 3×3** | **`ANNEAL`, `ALCHEMIST`** | "Three weeks in. We rise before the sun…" |
| PK8 | Q(4)Q(5)Q(6)Q(7) | `METE`, `METER`, `METIER`, `MASTERY` | "I leave at midnight…" *(unchanged)* |

Consequences:

* **The verified story arc is now complete through PK8** (investigation → the
  needle → the Whitesmith's apprenticeship → departure at midnight with one
  needle from the gutter, "the archive is my true calling, and the knot
  awaits.  I leave the Whitesmith a short letter.").
* Every previous PK9 crib corpus built from "PK1–PK7 plaintext windows" was
  partially **poisoned**: the PK4/PK5/PK7 windows were fabricated text.
* The author's key style is now systematic: every key so far is a thematic
  story/craft word (or, for PK5, the previous plaintext), and every
  transposition keyword has **distinct letters**.

## 2. Verified cipher conventions (all independently reproduced)

* **Quagmire III** ("KRYPTOS alphabet" = `KRYPTOSABCDEFGHIJLMNQUVWXZ`):
  `Kidx_out = (Kidx_in + Kidx(key[i mod len])) mod 26`; keystream starts at
  `key[0]` (verified on PK1, PK3, PK4, PK8).
* **Composition of Quagmire III layers over the same alphabet is additive**:
  Q(a)∘Q(b) = single substitution with shift `qa[i%|a|] + qb[i%|b|]`
  (verified on PK3's Q(8)Q(10) and PK8's Q(4)Q(5)Q(6)Q(7)).
* **Columnar transposition**: fill the rows×cols grid **row-wise**, permute
  columns by the keyword's alphabetical order, read out **column-by-column**
  (verified on PK2, PK4, PK5, PK6).  The site paraphrase "write in columns,
  swap columns, read by rows" is inaccurate.
* **Layer notation is encryption order** (PK4 `T(8)Q(5)Q(9)` is
  transposition-first; PK6 `T(9)T(9)Q(6)` likewise; PK8 all-Q).  Therefore
  **PK9 `Q(7)Q(6)Q(5)T(8)` = substitution first, columnar T(8) last** — the
  primary architecture assumed by the earlier exact-crib campaigns is
  confirmed.  The `tq` order is retained as an insurance hypothesis.
* The `RotatingTransposition` in the reference code is used only for the
  original sculpture's K3 — no PK puzzle uses it.
* `probe_pk4_layer_order.py` now **re-derives PK4 blind**: over all 8! column
  orders exactly one is consistent with a q5+q9 sum-clock, it equals
  `UNDERLAY`'s key order, and the gauge lift recovers the literal words
  `OCHRE` and `VERDIGRIS`.

## 3. New attack engine: `sweep_pk9_word_wheels.c`

A crib-free exhaustive sweep over (Q5-word × Q6-word × Q7-word × T8) for both
layer orders:

* wheels are literal vocabulary words; the T8 factor is either **all 8!
  permutations** or restricted to permutations induced by 8-letter keywords;
* quadgram scoring with a **sound branch-and-bound prefix filter**
  (threshold −5.8/char over the first 32 chars; every window of the verified
  story texts scores ≥ −5.16, so no true English prefix can be aborted);
* **validated end-to-end**: the built-in encryptor reproduces official PK4
  exactly, and a planted 144-letter control letter with keys
  `AWAIT/GUTTER/TEACHER + GRATEFUL` is recovered at **rank 1 of 3.04 billion
  candidates** (score −4.2905, next-best −5.45).

Throughput: 11–16M candidates/s on this 2-core sandbox.  Vocabularies are
built by `build_pk9_wheel_vocab_v2.py` from the **punctuated source texts**
(story word tokens + word-aligned spans such as `TWOYEARS`, `TENYEARS`,
`THEKNOT`), prior keys, Kryptos vocabulary and the repo's curated craft
lists.  (An earlier v1 builder tokenized the space-free normalized text and
produced a degenerate vocabulary; stage-1 results before 02:50 UTC used it
and were re-run.)

## 4. Results so far

All negative (best scores are deep in the noise band ≈ −6.7; a true break
scores −4.3…−4.9 — cf. the −4.29 control and PK8's −4.36):

| Stage | Wheels | T8 factor | Orders | Candidates | Best |
| :--- | :--- | :--- | :--- | ---: | ---: |
| R1 | story vocab (119×123×141) | 26 story-word perms | qt+tq | 107,318,484 | −6.9198 |
| R2 | story vocab | 284 theophilus-word perms | qt+tq | 210,509,334 | −6.8279 |
| R3 | PK8-plaintext windows (147³) | 284 theophilus-word perms | qt+tq | 324,005,346 | −6.8632 |
| R4 | deletion-ladder chains | all 8! | qt+tq | 79,833,600 | −6.9540 |
| C1 | crib: 1,929 corrected story windows, prefix | all 8! | qt | 77,777,280 | 0 full-crib hits |
| C2 | crib: same, all 127 offsets | all 8! | qt | 9,877,714,560 | 0 full-crib hits (word filter) |
| C3 | crib: same, unrestricted wheels | all 8! | qt | 9,877,714,560 | best survivor ≈ −6.42 (chance) |

Notes: C1–C3 re-run the earlier exact-crib machinery on **corrected** story
windows (the engine itself is unchanged and was already validated).  The
14.6M "full-crib survivors" in C3 are exactly the chance expectation for two
unconstrained check letters; none approaches English.

**Running** (`run_pk9_wheel_campaign.sh`, log: `pk9_wheel_campaign.log`):
R5 story-wheels × all 40,320 T8 permutations (qt), R6 broad-craft-wheels ×
story-word T8 (both orders), R7 broad wheels × theophilus-word T8 (qt),
R5b story wheels × all perms (tq), R8 PK8-window wheels × all perms (qt).

## 5. Interpretation

* PK9's wheels are **not** any triple of story/thematic words from the
  verified narrative (tokens or word-aligned spans), nor PK8-literal keys
  (earlier dihedral tests), nor deletion ladders — under any T8 keyword and
  both layer orders.
* The corrected story windows do **not** appear anywhere in PK9's plaintext
  under the verified architecture, even with fully unrestricted wheels.
* If the wheels are English words at all, they lie outside the current
  vocabularies (R6/R7 test the broad craft lists), or the T8 keyword lies
  outside story/theophilus vocabulary while the wheels are non-story words —
  the cross-product gap that motivates keeping all-permutation stages (R5)
  affordable only for the story-vocabulary wheel set.

## 6. Reproduction

```bash
# verify all eight constructions against the official ciphertexts
python3 kryptos/verify_pk_constructions.py

# blind re-derivation of PK4 (order + OCHRE/VERDIGRIS gauge lift)
python3 kryptos/probe_pk4_layer_order.py

# build vocabularies, then validate and run the sweep engine
python3 kryptos/build_pk9_wheel_vocab_v2.py
cc -O3 -march=native -funroll-loops -fopenmp -o /tmp/sweep_pk9_word_wheels \
   kryptos/sweep_pk9_word_wheels.c -lm
/tmp/sweep_pk9_word_wheels --self-test
/tmp/sweep_pk9_word_wheels kryptos/pk9_vocab_story5.txt \
   kryptos/pk9_vocab_story6.txt kryptos/pk9_vocab_story7.txt --order qt --top 10

# corrected-story crib campaign (existing engine)
python3 kryptos/generate_pk9_q567_windows.py /tmp/pk9_story18.txt \
   --length 18 --verified PK1 PK2 PK3 PK4 PK5 PK6 PK7 PK8
cc -O3 -march=native -fopenmp -o /tmp/crack_pk9_q567_t8_crib \
   kryptos/crack_pk9_q567_t8_crib.c -lm
OMP_NUM_THREADS=2 /tmp/crack_pk9_q567_t8_crib --word-filter-all-offsets /tmp/pk9_story18.txt
OMP_NUM_THREADS=2 /tmp/crack_pk9_q567_t8_crib --all-keys-all-offsets /tmp/pk9_story18.txt

# the staged background campaign
bash kryptos/run_pk9_wheel_campaign.sh   # log: kryptos/pk9_wheel_campaign.log
```

## 7. Next steps if the campaign ends negative

1. **Widen the wheel vocabulary along the author's demonstrated key style**
   (pigment/patina colours like OCHRE and VERDIGRIS, metalwork process words,
   textile terms) — the curated lists cover some of this; a dedicated
   colour/material list would close the gap that R6/R7 approximate.
2. **A joint (wheels × T8) hill-climb with the exact crib solver as the
   proposal mechanism** — for each T8 permutation, solve the 16 effective
   wheel coordinates from the *current best* quadgram-guided pseudo-crib and
   iterate; this couples dictionary knowledge to the transposition without a
   real crib (the direction the previous session's report called for).
3. **Broader crib sources from the corrected story**: the letter PK8 promises
   ("I leave the Whitesmith a short letter") argues for regenerating the
   short-letter corpora with true story details (inner door, winter fodder,
   stone barn, Pellegrin, Bern, ten years) — the previous letter generators
   predate the corrected texts.
4. PK5's precedent (previous plaintext as key) is only partially explored:
   R3/R8 test PK8 windows as wheels; the analogous "PK8 plaintext as the
   T8-key source" is covered by the all-permutation stages R5/R5b.

---

## Session addendum (2026-10-02, later): statistical investigation, order tests, tq engine

### Raw-ciphertext statistics and what they actually prove

PK9 raw profile (N=144): IoC(7)=0.0568 vs 0.0445 overall; autocorrelation
z(lag7)=+3.88, z(lag14)=−0.46, z(lag21)=+1.53, z(lag28)=+3.64; repeated
ciphertext bigram XG (pos 82/89), bigram GU (90/97), trigram UQG (119-121 =
126-128), all at lag 7.  Reference behaviour on solved puzzles:

| puzzle | construction | statistic | value |
|---|---|---|---|
| PK4 | T(8)Q(5)Q(9), Q last, period 45 | IoC(45) | **0.0756** |
| PK6 | T(9)T(9)Q(6), Q last, period 6 | IoC(6) | **0.0699**, lag-6 z=+2.70 |
| PK5 | Q last but period 224 > N | — | no peaks |
| PK8 | pure Q sum-clock, period 420 > N | IoC(7) | 0.0536 (mild), z(7)=+0.17 |
| PK7 | Q first, Hill last | — | nothing |

A Monte Carlo with UNIFORM random wheels (4,000 trials per family) showed no
qt/tq/pure family ever reproduces PK9's joint z7+z28 profile — suggesting an
anomaly.  **A planted control overturned this**: a tq cipher with REAL keyword
wheels (METER/METIER/MASTERY, T8 key UNDERLAY, story plaintext) naturally
produces lag7=11, lag14=8 matches with ZERO exact keystream equalities — all
coincidental, because clustered keyword letters (KRYPTOS indices of common
letters) concentrate the s-difference distribution.  Conclusion: **the
period-7 statistics do not discriminate layer order or model**; they are the
expected behaviour of any Q(5)+Q(6)+Q(7)+T(8) with author-style keyword
wheels.  (Lesson: always validate statistical arguments against planted
controls before believing a Monte Carlo null.)

A dictionary search for wheel pairs satisfying 5 exact t-equality constraints
"derived" from the structural repeats (10,177 x 17,685 words) found 18 pairs
vs ~15 expected by chance — no signal, consistent with the control.

### New engines (all with planted self-tests)

- `crack_pk9_t8_q7.c` — exact crib solver for reduced models T8+Q(7) in both
  orders (period-7 wheel only).  Self-consistent; run on the letter corpus.
- `crack_pk9_tq_grouped_cribs.c` — exact crib solver for the TQ order
  (T8 FIRST, then the Q567 sum-clock), the previously untested layer order.
  Linear algebra over Z26 via CRT (mod 2 + mod 13), handling:
  - the 2-dimensional gauge of the 3-wheel sum-clock
    (q5+a, q6+b, q7−a−b give identical ciphertext — same gauge as the PK4
    probe, one dimension per extra wheel);
  - the structural fact that an L-letter consecutive crib covers only
    ceil(L/8) of the 6 q6 residues (m%6 advances once per 8 letters), so
    30-letter cribs leave 2 q6 values free (enumerated for survivors).
  Self-test: 60/60 random planted permutations recovered exactly.
- `climb_pk9_period7.c` — (sigma, q7) hill-climb with per-coset chi-square
  init, both orders.  Self-test shows the climb gets trapped in local optima
  even given the true sigma (recovered score −4.82 vs true −4.36), so its
  negative results are weak; parked in favour of exact crib solvers.
- `montecarlo_pk9_profile.py`, `constraint_search_pk9_wheels.c` — analysis
  tooling for the above.

### New negative results (letter corpus = 16,985 corrected-story 30-letter
openings in /tmp/pk9_letter30_corrected.txt, regenerated via
`generate_pk9_letter_corrected_story.py`; all at crib offset 0, all 8! T8
orders, all wheel values):

| engine | model | placements | survivors |
|---|---|---|---|
| split word-filter (existing engine) | Q56->T8->Q7, story wheels | 6.85e8 | 0 |
| crack_pk9_t8_q7 --tq/--qt | T8+Q7 only, both orders | 2 x 6.85e8 | 0 |
| crack_pk9_q567_t8_crib --all-keys | qt grouped | 6.85e8 | 0 |
| crack_pk9_tq_grouped --all-keys | **tq grouped** | 6.80e8 | 0 |

None of the 16,985 guessed openings fits at offset 0 under any grouped or
Q7-only model, either order, with arbitrary wheels.

### Campaign / resource notes

- The R5 campaign stage (story wheels x all-40320 T8 qt) was stopped ~60% in
  to free cores for the exact crib runs; no result recorded for R5.  The
  campaign restarts as Stage C of the overnight pipeline.
- Overnight pipeline (running): (A) qt all-offsets on a diverse 2,831-crib
  subset of the letter corpus; (B) tq all-offsets same; (C) full wheel-word
  campaign R5-R8.  Log: `kryptos/pk9_overnight_pipeline.log`.

### Standing conclusions

1. Crib machinery remains the only proven approach; every architecture x
   order x wheel-space combination reachable by exact solvers has now been
   tested negative on prefix cribs — the bottleneck is CRIB RECALL (guessing
   the true opening), not solver coverage.
2. The gauge freedom means any wheel solution found is only defined modulo
   (a, b, -a-b); keyword identification must sweep the 676 gauge classes.
3. Highest-value remaining directions: all-offsets runs (in progress), new
   crib corpora from different narrative framings (e.g. the letter being
   FROM the Whitesmith, or written years later), and the word-wheel campaign
   (no-crib coverage of all T8 orders).

---

## Session addendum 2 (2026-10-02 evening): chi-square wheel filter, corpus v2, pipeline

### Sigma-free chi-square wheel filter (TQ order) — new tool `chisweep_pk9_tq.c`

Under tq the letter MULTISET of P-hat[i] = C[i] - q5[i%5] - q6[i%6] - q7[i%7]
equals the plaintext multiset regardless of the T8 permutation (a
transposition only permutes positions).  Planted controls: true wheels give
chi-square 23.2 vs best-of-2000 random wheels 261.8.  Word-triple sweeps with
this filter (each followed by full 8! verification of survivors):

| vocab | triples | below chi2<120 | best quadgram |
|---|---|---|---|
| story 119x123x141 | 2.06e6 | 1 (chi2 116.9) | -6.96 noise |
| broad 633x707x587 | 2.63e8 | 117 (best 75.6) | -6.98 noise |
| theophilus 833x928x796 | 6.15e8 | 295 (best 79.1) | -7.08 noise |
| curated 559x616x471 | 1.62e8 | 68 (best 79.1) | -7.08 noise |
| pk8win 147^3 | 3.18e6 | 0 | - |
| ladder 9x10x11 | 990 | 0 | - |

**TQ + word wheels is now exhaustively NEGATIVE for all supplied
vocabularies** (this supersedes the campaign's tq stages R5b/R6-tq/R8-tq,
which are hereby cancelled — the filter covers the same space including all
40320 T8 orders, in seconds).

Non-word wheels: a 60,000-restart coordinate descent on the chi2 landscape
finds 30,000+ distinct minima below chi2=65 (18 free parameters overfit the
26-bin multiset easily); even chi2=18.5 minima verify at -6.5 (noise).  The
filter therefore CANNOT discriminate non-word tq wheels; that space remains
open only via crib solvers.

A similar multiset statistic for the QT order was tested and shows NO
discrimination (true 22.1 vs random median 23.2 — expected-count vectors are
nearly flat for any wheels), so the qt side still requires brute sweeps.

### Letter corpus v2 (`generate_pk9_letter_v2.py`)

Adds the missing opening framings: "Three weeks in" (the author's time-marker
series: PK3 "Seventh month.", PK4 "Two years in.", PK5 "Fourteen days in the
barn.", PK7 "Three weeks in."), "By the time you read this", "When you read
this", "I am writing this", candlelight/lamplight, "I will miss", "I will
never forget", workshop imagery, with PK6-PK8 vocabulary continuations.
618 new cribs (>= 21 letters; 578 of them >= 28).

Prefix results (all engines, all 8! T8 orders, all wheels): tq grouped 0/24.9M,
qt grouped 0/24.9M, Q7-only both orders 0/24.9M placements.

### All-offsets crib results (crib anywhere in the 144 letters)

- qt grouped, top-2831 v1 subset: 13.1e9 candidates, **0 full-crib hits**
  (216 s at 60.7M candidates/s — the qt engine's early-abort is excellent).
- qt grouped, v2 subset >= 28 letters: 2.7e9 candidates, **0 hits**.
  (An unfiltered v2 run showed 10 "hits" that were all artifacts of 21-letter
  cribs — expected ~344 false positives at that length; keep all-offsets
  cribs to >= 28 letters.)
- qt grouped, FULL 16,985-crib v1 corpus: running (78.8e9 candidates).
- tq grouped, top-2831: in overnight pipeline (~4 h).

### Overnight pipeline (running, `kryptos/pk9_overnight_pipeline.log`)

P1 story-wheels x all-40320-T8 qt | P2 broad x story-T8 qt | P3 pk8win x
all-T8 qt | P4 broad x theophilus-T8 qt | P5 qt all-offsets (top-2831;
already done negative, kept for completeness) | P6 tq all-offsets (top-2831)
| P7/P8 v2-corpus all-offsets both orders.

### Updated standing conclusions

1. TQ + word wheels: exhaustively negative (chi-square filter, all T8 orders).
2. QT + word wheels: R1-R4 negative on partial T8 sets; P1-P4 will complete
   story/broad/pk8win wheels x the relevant T8 sets tonight.  Remaining qt
   word gap: full all_words cross-product (infeasible: ~4e12+ triples) —
   would need a qt prefilter, none found (multiset statistic is blind there).
3. Crib recall remains the binding constraint for all-keys modes: 17,603
   opening guesses (v1+v2) are negative at prefix; qt all-offsets negative on
   the top-2831; full-corpus and tq all-offsets pending.
4. Non-word wheels: unreachable by filters on either order (overfitting);
   only exact cribs or brute sweeps can find them.
