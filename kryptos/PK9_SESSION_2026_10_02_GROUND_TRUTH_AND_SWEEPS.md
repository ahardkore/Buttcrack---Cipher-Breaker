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
