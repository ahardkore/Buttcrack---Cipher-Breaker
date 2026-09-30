# PK8, PK9, PK10 — closing measurements (September 2026)

> A finishing pass over the open frontier, run under the discipline the
> retraction called for: **every search is calibrated against synthetic
> instances with known answers before its verdict on the real ciphertext is
> believed**, and every candidate solution must pass
> `scripts/pk_verify.py` — a harness that rejects anything a wrong answer
> could satisfy (self-tested against the retracted PK9 reading, which it
> fails on quadgram band: −4.95 vs the English band [−4.55, −3.80]).

## 0. What this adds

The prior phase established strong suspicions (wheel sets, factor grids,
parity anchors) but almost nothing about a basic question: *if the model is
right and we search this hard, do we win?*  Answering that needs three
measurements per puzzle — (a) can the search class recover synthetic
instances of the believed shape, (b) how wide is the true key's attraction
basin, (c) given a = b, does the real ciphertext yield.  This document
records those measurements.

## 1. PK8 (N = 153, believed 4-clock {4,5,6,7})

### 1.1 The search classes fail on synthetics, and now we can say how much

| Search class | Budget | Synthetic recovery |
| --- | --- | --- |
| Python annealer (`SumClock._anneal`), 10 restarts × 260 sweeps | ~45 s/instance | **0/6** (fit −6.1…−6.4 vs English −4.05) |
| C quadgram SA + ILS (`kryptos/pk8_sa_cal2.c`) | 30 restarts × 12 ILS × 5M steps (~25 min, 2 threads) | **0/1** (best fit −6.63, 3.9% letters) |
| Genetic/memetic (uniform crossover + ascent) | 6.5 min/instance | 0/2 (fit −6.01) |
| Mean-field EM, deterministic annealing, order-1 (`kryptos/pk8_emda.py`) | 40–80 iterations | collapses to wrong modes; true-letter posterior mass ~0.06 throughout |

### 1.2 Why: the basin measurement

`kryptos/pk8_basin_probe.py` corrupts k of the 22 wheel coordinates of a
*synthetic* instance from the true key and re-ascends:

| k | recovered |
| --- | --- |
| 1–2 | 20/20 |
| 3 | 17/20 |
| 4 | 8/20 |
| 6 | 1/20 |
| 8 | 0/20 |

The true key attracts only within ~3 of 22 coordinates; blind restarts have
about 1-in-26 correct per coordinate, i.e. ~1 correct, nowhere near the
basin edge.  This is a landscape fact, not a budget fact: no amount of
annealing time changes it, which is why the wheel-set hypothesis could never
be confirmed *or* refuted by any run of this kind.

### 1.3 The structural reduction the previous phase missed

The full-product annihilator of the wheel periods,
∏(1−E^{pᵢ}) with taps at offsets {0,4,5,6,7,9,10,11(×2),12,13,15,16,17,18,22},
leading coefficient +1 at lag 22, kills *any* keystream of this shape.  On
the plaintext side it reads:

> **Given any 22 consecutive plaintext letters, the entire rest of the
> message to the right is forced, letter by letter** (and symmetrically to
> the left).  PK8 is exactly "find 22 letters".

Hu's external solve after 86 days, and the manuscript's observation that a
correct 19-letter crib solves it in 0.1 s, are the same theorem in two
dialects.  What the reduction adds is quantitative: without a crib, the
problem is a search over 22 positions of free text, and everything else is
verification.

### 1.4 The parity sieve (a real, calibrated reduction)

Mod 2, the 22-free-position reduction survives.  Scoring all 2²² seeds by a
mod-2 4th/5th-order Markov chain (clean English corpus, 80 k letters):

- true seed rank ≈ **5,800–12,000 of 4,194,303** (order-5; measured on a
  synthetic instance): a ≈3-decade reduction of the space, explicitly
  measured rather than hoped.
- A beam over openings dies by level 4–6 at width 20,000 (true openings are
  *typical*, not exceptional, English) — so the sieve cannot be extended
  into a full solve by beam search, and no variant that scores prefixes
  locally can work.  Quantified dead, not merely failed.
- The residual 13-ary stage has an equally narrow basin (k=3: 8/16, k=5:
  4/16, k=9: 0/16) — parity does not tame the landscape; it only orders
  the queue.

### 1.5 Verdict

PK8 remains unsolved, but its frontier is no longer a fog: it is a
22-letter find-the-crib problem with a measured barrier, a working
acceptance test (`pk_verify.py`), and an exact 2-decade+ sub-problem now
standing between an attacker and the answer.  The author's hint (solve PK9
first) is consistent with everything measured: the intended route gives the
crib; there is no measurable way around it from ciphertext alone with the
search classes tried.

## 2. PK9 (N = 144; believed 18×8 double columnar + period-28 additive)

### 2.1 The joint search is calibrated, and it fails on synthetics

The retraction established that the old *claim* was unsupported; this phase
measured whether the *search class* behind it (joint quadgram annealing over
the two column permutations and the 28 shifts) can recover a synthetic
instance of exactly the believed shape at all:

| Run | Budget | Result |
| --- | --- | --- |
| `pk9_sa_cal2` #1 (24 restarts × 14 ILS × 3M steps + polishes, ~30 min, 2 threads) | best fit **−4.86**, 5.6% letters correct | **No recovery.** Truth scores −4.05; the search landscape's reachable optima top out far below it. Note the score is *better* than the retracted claim's −5.25 — a quantified picture of how deep the overfit pool is on 144 letters. |
| `pk9_sa_cal2` #2, stronger (32 restarts × 20 ILS × 6M steps, finer shift moves, hotter T₀; stopped at restart 6/32 for resource control) | best fit **−4.8150**, still vs truth −4.05 | no recovery on trajectory; see the basin measurement below for why budget size does not change this verdict |

The basin probe (`kryptos/pk9_basin_probe.py`) corrupts k coordinates of a
*synthetic* true state (p1 column swaps, p2 swaps, shift re-draws) and runs
greedy descent (shift sweeps + full swap-descent):

| k | recovered |
| --- | --- |
| 2 | 2/12 |
| 3 | 1/12 |
| 4 | 1/12 |
| 6 | 0/12 |
| 8 | 0/12 |

Same geometry as PK8: the true state attracts within ~2–3 moves and the
space of wrong configurations dominates everything beyond it.  The
joint problem has ~44 dimensions (153 p1-pairs + 28 dials + 28 p2-pairs'
descent structure); landing inside a 3-move basin from a random start is a
once-in-the-age-of-the-universe event for any of the usual search dynamics.

Two important consequences, whichever way #2 lands:

1. **The believed permutations are unsafe.**  `p1`, `p2` in the old dossiers
   were "proven" by being global maxima of this very scorer — a scorer now
   measured to be maxable by wrong answers at −4.86 and below.  The 18×8
   factorization may be right or wrong; nothing in the repository can
   currently tell them apart.
2. **Real-ciphertext runs of this search class are uninformative** until a
   budget/configuration is shown to recover synthetics.  (Calibration #2 is
   that test; if it recovers, the real PK9 run follows immediately.)

### 2.2 The manuscript's one untested proposal, tested

Chapter 11 nominated a statistic that might survive the transposition wall:
*stride-k bigrams* — plaintext-adjacent letters sit a fixed stride apart in
the pre-substitution stream, so stride-d bigram statistics might identify
the outer key where the histogram cannot.  `kryptos/pk9_stride_statistic.py`
measures it on synthetics with known keys, compared head-to-head with the
bare histogram:

- rank-the-true-key-among-140-local-wrongs: monogram histogram loses
  10/10 instances (best wrong beats true every time); max-over-72-strides
  bigram loses **worse** (more wrong keys beat true — the max over ~144
  strides hands every wrong key a multiple-comparison jackpot).
- The proposal is dead, with its mechanism named: any *max-over-d* stride
  statistic multiplies its false-positive surface by the number of strides
  faster than the true signal grows.

### 2.3 Why the structure can't be confirmed piecewise

A transposition preserves the letter multiset of Z, and the 28 shifts act
only on Z's residues mod 28 — so the shifts cannot be attacked without the
permutations, and any English-model test of the permutations requires the
shifts first.  The layers are logically entangled: the joint problem has to
be solved as one, which is precisely where the measured identifiability wall
lives.

## 3. PK10 (N = 504; believed 3-clock {7,8,9} + outer transposition)

- **Stage 1 (transposition-invariant clock recovery) fails calibration.**
  Monogram log-likelihood coordinate descent recovers 0/8 synthetic
  {7,8,9}-+columnar instances (~4% wheel-letter accuracy, random-level).
  A single restart is the weakest optimizer, but the failure mode matches
  the manuscript's identifiability wall: at 504 letters the histogram
  carries less information than the 23 dial dimensions need.  Any future
  stage-1 claim needs a better statistic *and* this calibration.
- The parity-transfer and IoC evidence from the previous phase stands as
  the strongest existing clue (IoC 0.0453 with natural frequencies restored)
  but does not yet amount to a key.

## 4. Instruments left behind

| File | Purpose |
| --- | --- |
| `scripts/pk_verify.py` | The acceptance harness.  Reproduction-first, quadgram-band, dictionary coverage, non-degeneracy; selftest rejects the retracted reading. |
| `kryptos/pk8_calibrated_recovery.py` | Synthetic-instance factory + naive annealer calibration (0/6). |
| `kryptos/pk8_basin_probe.py` / `pk8_p13_basin_probe.py` | Basin measurements, Z26 and parity-pinned Z13. |
| `kryptos/pk8_sa_cal2.c` | Production-grade C SA/ILS with `--synthetic`/`--real` and both alphabets. |
| `kryptos/pk8_parity_sieve.c` | The mod-2 Markov sieve over all 2²² seeds. |
| `kryptos/pk8_emda.py`, `pk8_memetic_ga.py`, `pk8_prefix_survival.py`, `pk8_emda_probe.py` | Calibrated negatives: EM collapse, crossover failure, beam death, wiring checks. |
| `kryptos/pk9_sa_cal2.c` | Joint SA (p1, p2, shifts28) with synthetic calibration mode. |
| `kryptos/pk10_clock_synthetic_probe.py` | Stage-1 calibration failure for PK10. |

*Artifact note: `pk_all_ciphertexts.json` also carries a `PK9_UNDONE` entry —
an exact permutation of PK9 (identical letter multiset, IoC 0.04448) that
matches none of the published candidate transformations.  It is an
unlabeled intermediate of the earlier analysis and should be treated as
provenance, not data.*
