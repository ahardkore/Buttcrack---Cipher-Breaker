# PK9 `Q(5)+Q(6)+Q(7) -> complete T(8)` Exact-Crib Report

**Date:** 2026-10-01

**Status:** no solution; bounded negative results under an unverified architecture

## Scope and assumptions

This experiment tests the tentative construction

```text
plaintext -> additive Q5+Q6+Q7 over KRYPTOSABCDEFGHIJLMNQUVWXZ
          -> complete 18-row, 8-column transposition -> PK9 ciphertext
```

where the eight output blocks are a permutation of the eight grid columns. This
architecture is a hypothesis inferred from an unverified public description. It
is not established by the official clues, and a failure here does not disprove
PK9 or any other architecture.

The additive key has 18 raw coordinates and two gauge freedoms. Setting
`q5[0] = q6[0] = 0` leaves 16 effective coordinates. For every tested offset,
the 16-by-16 design matrix for 16 consecutive plaintext positions is invertible
modulo 2 and modulo 13, hence modulo 26. Therefore:

1. choose a plaintext crib placement;
2. choose one of the `8! = 40,320` transposition block assignments;
3. solve exactly for all 16 effective wheel coordinates;
4. verify every crib letter beyond the determining first 16;
5. optionally require gauge-equivalent literal dictionary words of lengths 5,
   6, and 7;
6. decrypt and quadgram-score every survivor.

The implementation is `crack_pk9_q567_t8_crib.c`. It is an exhaustive test of
the stated finite candidate set, not a heuristic key search.

## Dictionary-key filter

The filter loads the repository's broad `all_words.txt`, `words_5.txt`,
`words_6.txt`, and `words_7.txt` lists. Input-entry counts (including duplicates
between files) are 25,902 length-5, 47,343 length-6, and 65,721 length-7 words.

For each word, the filter removes its first-letter shift and stores:

- the four relative coordinates of a 5-letter word in a dense `26^4` table;
- the five relative coordinates of a 6-letter word in a dense `26^5` table;
- the six relative coordinates of a 7-letter word in a sparse hash table.

Each value is a 26-bit mask of possible first letters. The final mask check
accounts exactly for the two gauge shifts, so it accepts a recovered normalized
key iff at least one gauge-equivalent `(word5, word6, word7)` triple occurs in
the loaded lists. Optional `--word-filter-t8` modes also stable-sort each supplied
8-letter word alphabetically, deduplicate the resulting complete-columnar
permutations, and enumerate only those T8 assignments.

A planted `STEEL / SILVER / DRAWING` control passes the filter, recovers the
known block assignment, and decrypts all 144 letters exactly. A second end-to-
end control uses the thematic T8 key `LANGUAGE` and also recovers all 144
letters. The unrestricted arbitrary-wheel planted control still passes.

## Real-PK9 results

### Curated craft phrases, all valid offsets

The 110 cribs have lengths 16 through 24. Testing only placements at which the
whole phrase fits gives:

```text
cribs=110
placements=13,957
permutations=40,320
candidates=562,746,240
elapsed=14.831 s (32 threads)
word_key_hits=0
full_crib_hits=0
```

Thus none of these exact strings yields three broad-dictionary wheels anywhere
in the 144-character plaintext under the hypothesized architecture.

### Expanded grammar phrases, all valid offsets

All 2,750 entries are 18 letters, giving 127 valid placements each:

```text
cribs=2,750
placements=349,250
permutations=40,320
candidates=14,081,760,000
elapsed=327.535 s (32 threads)
rate=42.993 million candidates/s
word_key_hits=4
full_crib_hits=0
```

The four recovered keys satisfying the independent dictionary condition all
failed one of the two extra crib letters. They are random coincidences, not
candidate decryptions. Earlier diagnostic output ranked these after forcing only
the determining 16 letters; the current solver verifies the entire supplied
crib and correctly reports zero full-crib survivors.

### Broad generated narrative phrases

`generate_pk9_q567_prefixes.py --length 18` deterministically generates 324,860
distinct 18-letter narrative, craft, archive, knot, and cipher-text openings.
At offset zero, with unrestricted T8:

```text
cribs=324,860
placements=324,860
permutations=40,320
candidates=13,098,355,200
elapsed=269.789 s total (two disjoint batches, 32 threads)
word_key_hits=40
full_crib_hits=0
```

A second test allowed every valid plaintext offset while restricting T8 to the
284 distinct stable alphabetical permutations induced by the 287 eight-letter
Theophilus vocabulary words:

```text
cribs=324,860
placements=41,257,220
permutations=284
candidates=11,717,050,480
elapsed=300.669 s total (two disjoint batches, 32 threads)
word_key_hits=3
full_crib_hits=0
```

All dictionary-key coincidences failed the seventeenth or eighteenth crib
letter. These tests reject the generated phrases at the prefix under arbitrary
T8, and anywhere in the plaintext under the additional thematic-T8 assumption.

### Published PK1-PK7 plaintext windows, all offsets

Every distinct 18-letter window of the verified PK1-PK7 plaintexts was tested
at every valid PK9 placement. The PK6-PK7 narrative subset and PK1-PK5 remainder
were run separately; together they cover 1,793 cribs, 227,711 placements, and
9,181,307,520 candidate keys. Four candidates had three broad-dictionary wheel
keys, but none matched both extra crib letters:

```text
word_key_hits=4
full_crib_hits=0
```

### Theophilus Book III source windows

The normalized local source corpus contains 289,847 distinct 18-letter windows.
First, every window was tested as a PK9 opening under unrestricted T8:

```text
placements=289,847
permutations=40,320
candidates=11,686,631,040
elapsed=278.473 s (32 threads)
word_key_hits=8
full_crib_hits=0
```

Then every source window was tested at all 127 valid PK9 placements while T8
was restricted to the 284 distinct permutations induced by the 287 thematic
8-letter words:

```text
placements=36,810,569
permutations=284
candidates=10,454,201,596
elapsed=298.168 s (32 threads)
word_key_hits=5
full_crib_hits=0
```

This rules out an exact 18-letter source quotation anywhere only under the
additional thematic-T8 and broad Q-wheel dictionary assumptions. It does not
rule out paraphrase, a non-word transposition key, or another architecture.

## Verified PK8 bridge experiments

### Exact PK8 solution and positive control

A [public implementation](https://github.com/TTFH/KRYPTOS/commit/3d60736f)
now gives PK8's exact construction: four sequential Quagmire III layers over
the KRYPTOS alphabet, with keywords `METE`, `METER`, `METIER`, and `MASTERY`. Independent local encryption reproduces the official
153-letter PK8 ciphertext exactly. Its plaintext is:

```text
ILEAVEATMIDNIGHTBEFOREGOINGIPICKUPONENEEDLEFROMTHEGUTTERIAMGRATEFULTOMYTEACHERBUTTHEARCHIVEISMYTRUECALLINGANDTHEKNOTAWAITSILEAVETHEWHITESMITHASHORTLETTER
```

The answer is recorded with its SHA-256 checksum in
`pk_verified_solutions.json`. As an end-to-end positive control, every tested
real-PK8 plaintext window at its correct placement recovers the exact plaintext
through the unrestricted PK8 crib solver, with whole-text score `-4.361307`.
This confirms the crib equations, placement convention, and language scorer on
a real challenge rather than only planted synthetic data.

### Literal PK8 key reuse

PK8's shared-length keys provide the most direct key hypothesis for PK9:
`METER` (Q5), `METIER` (Q6), and `MASTERY` (Q7). Every width-8 complete-columnar
read order was tested in both possible layer orders:

```text
Q5+Q6+Q7 -> T8: best score -7.130210 across 40,320 orders
T8 -> Q5+Q6+Q7: best score -7.726318 across 40,320 orders
```

Both best plaintexts are noise. Literal reuse therefore fails even if the
public architecture notation listed decryption order rather than encryption
order.

A wider finite test independently rotated and optionally reversed each of the
three PK8 wheels. There are `(2×5)(2×6)(2×7) = 1,680` such dihedral transforms.
Combining each with every T8 permutation tested 67,737,600 states per layer
order:

```text
Q5+Q6+Q7 -> T8: best score -6.744215
T8 -> Q5+Q6+Q7: best score -6.878823
```

Again, every result is noise. This excludes literal PK8 coordinates under
independent phase changes and reversals, but not arbitrary substitutions,
anagrams, or a more general PK8-derived key schedule.

### Literal PK8 windows in PK9

Every one of PK8's 136 overlapping 18-letter plaintext windows was tested at all
127 valid PK9 offsets, with all 40,320 T8 permutations and the broad Q5/Q6/Q7
dictionary filter:

```text
cribs=136
placements=17,272
permutations=40,320
candidates=696,407,040
full_crib_hits=0
```

Thus PK9 does not repeat an exact 18-letter PK8 plaintext substring under the
stated architecture and word-wheel assumption.

### Focused continuations from PK8's ending

`generate_pk9_from_pk8.py` deterministically constructs 77,200 distinct
20-letter narrative continuations motivated by PK8's departure, short letter,
archive, knot, needle, route, and destination. Four exhaustive tests were run:

| Q coordinates | T8 assignments | placements | candidates | result |
| --- | --- | ---: | ---: | --- |
| broad dictionary words | all 40,320 | prefix only | 3,112,704,000 | 0 full-crib hits |
| broad dictionary words | 293 thematic permutations | all 125 offsets | 2,827,450,000 | 0 full-crib hits |
| unrestricted effective coordinates | all 40,320 | prefix only | 3,112,704,000 | 7,095 full-crib survivors; best score `-6.603156` |
| unrestricted effective coordinates | 293 thematic permutations | all 125 offsets | 2,827,450,000 | 6,232 full-crib survivors; best score `-6.648171` |

The unrestricted survivor counts are close to chance expectation: the first 16
letters determine the 16 effective coordinates, leaving four independently
checked letters. Every surviving whole plaintext is noise; none approaches the
verified PK8 control score of `-4.361307`. This removes the literal-word
assumption from the Q wheels for the full-T8 prefix test, and from all placements
when T8 belongs to the targeted set. It still does not exclude a non-targeted T8
permutation away from the prefix, an ungenerated continuation, or a different
PK9 construction.

### The short-letter hypothesis

PK8 ends with the unusually specific sentence, "I leave the Whitesmith a short
letter." `generate_pk9_letter_from_pk8.py` therefore models PK9 as that letter:
salutations, gratitude, departure explanations, the archive, the knot, taking
one needle, warnings, and farewells. It produced 2,468 distinct 20-letter
openings and 52,206 distinct windows. Unrestricted-Q exact tests found:

| crib set | T8 assignments | placements | candidates | survivors | best score |
| --- | --- | ---: | ---: | ---: | ---: |
| 2,468 openings | all 40,320 | prefix only | 99,509,760 | 236 | `-6.824992` |
| 52,206 windows | all 40,320 | prefix only | 2,104,945,920 | 4,619 | `-6.708400` |
| 52,206 windows | 284 Theophilus-word permutations | all 125 offsets | 1,853,313,000 | 4,042 | `-6.659011` |

All survivor counts are consistent with chance after four check letters, and
all whole-text decryptions are noise. Thus none of the generated letter
language is present at the opening under arbitrary T8, or elsewhere under the
Theophilus-word T8 set. The test does not exclude different wording or a
non-Theophilus T8 permutation away from the opening.

### PK8-calibrated narrative style

A limitation of hand-built continuation lists is unknown recall. To measure it,
`generate_pk9_style_from_pk8.py` models syntax visible in PK8—first-person
present tense, temporal complements, subordinate `BEFORE/AFTER` clauses, and
`BUT/AND` pivots—without inserting its complete opening as a fixed phrase. The
grammar generates 41,382 distinct 20-letter openings and includes PK8's actual
opening, `ILEAVEATMIDNIGHTBEFO`, through its ordinary token combinations.

As a real-answer positive control, the unrestricted PK8 crib solver tested all
41,382 openings. It recovered the exact PK8 plaintext at rank 1 with score
`-4.361307`; the next candidate scored only `-7.016394`. Applying the same
finite corpus to PK9 gave:

| target | T8 assignments | placements | candidates | survivors | best score |
| --- | --- | ---: | ---: | ---: | ---: |
| PK9 prefix | all 40,320 | 41,382 | 1,668,522,240 | 3,661 | `-6.667399` |
| all PK9 offsets | 284 Theophilus-word permutations | 5,172,750 | 1,469,061,000 | 3,230 | `-6.734873` |

A second grammar corrects an earlier past-tense bias and generates 51,950
present-tense openings around returning to the archive and using the needle on
the knot. Its arbitrary-T8 prefix sweep covered 2,094,624,000 states (4,574
chance survivors; best `-6.757267`), while its all-offset Theophilus-T8 sweep
covered 1,844,225,000 states (3,941 survivors; best `-6.734428`). No result is
language-bearing. The calibrated positive control makes this exclusion stronger
than an untested phrase list, but it still establishes recall only for PK8's
known opening—not for unknown PK9 wording.

Because the public hint said PK9 would likely help with PK8, a separate corpus
models explicit disclosure of `METE / METER / METIER / MASTERY`. Its 8,271
20-letter windows produced only chance survivors at the PK9 prefix under every
T8 permutation (333,486,720 candidates; best score `-6.849365`) and at every
offset under the 293 targeted T8 permutations (302,925,375 candidates; best
score `-6.831328`). A sharper test concatenated all 24 orders of the four words,
yielding 72 distinct 20-letter windows, and swept them at all 125 offsets with
all 40,320 T8 permutations and unrestricted Q coordinates. Among 362,880,000
candidates, 799 passed the four check letters—as expected by chance—and the best
whole-text score was only `-6.634722`. Thus PK9 does not literally contain 20
consecutive letters from any unseparated ordering of all four PK8 keys under the
proposed construction.

## Reproduction

From the repository root:

```bash
python3 kryptos/verify_pk8_solution.py
python3 kryptos/test_pk8_pk9_key_reuse.py

cc -O3 -march=native -fopenmp kryptos/test_pk8_pk9_transformed_keys.c \
  -o /tmp/test_pk8_pk9_transformed_keys -lm
OMP_NUM_THREADS=32 /tmp/test_pk8_pk9_transformed_keys --self-test
OMP_NUM_THREADS=32 /tmp/test_pk8_pk9_transformed_keys

cc -O3 -march=native -fopenmp kryptos/crack_pk9_q567_t8_crib.c \
  -o /tmp/crack_pk9_q567_t8_crib -lm

OMP_NUM_THREADS=16 /tmp/crack_pk9_q567_t8_crib --self-test
OMP_NUM_THREADS=16 /tmp/crack_pk9_q567_t8_crib --word-self-test
OMP_NUM_THREADS=16 /tmp/crack_pk9_q567_t8_crib --word-t8-self-test

python3 kryptos/generate_pk9_q567_prefixes.py \
  --length 18 /tmp/pk9_q567_prefixes18.txt
python3 kryptos/generate_pk9_q567_windows.py \
  /tmp/theophilus_windows18.txt --theophilus
python3 kryptos/generate_pk9_q567_windows.py \
  /tmp/pk1_7_windows18.txt --verified PK1 PK2 PK3 PK4 PK5 PK6 PK7

OMP_NUM_THREADS=32 /tmp/crack_pk9_q567_t8_crib \
  --word-filter /tmp/pk9_q567_prefixes18.txt

# Test every placement at which the full crib fits:
OMP_NUM_THREADS=32 /tmp/crack_pk9_q567_t8_crib \
  --word-filter-all-offsets CRIB_FILE

# Also require T8 to be induced by a word from the supplied 8-letter list:
OMP_NUM_THREADS=32 /tmp/crack_pk9_q567_t8_crib \
  --word-filter-t8-all-offsets kryptos/theophilus_w8.txt CRIB_FILE

# Reproduce the PK8-continuation corpus, then remove the Q-word assumption:
python3 kryptos/generate_pk9_from_pk8.py /tmp/pk9_from_pk8_20.txt
python3 kryptos/generate_pk9_from_pk8.py --key-disclosures \
  /tmp/pk8_key_disclosures_20.txt
python3 kryptos/generate_pk9_from_pk8.py --key-sequences \
  /tmp/pk8_key_sequences_20.txt
python3 kryptos/generate_pk9_letter_from_pk8.py --all-windows \
  /tmp/pk8_letter_windows_20.txt
python3 kryptos/generate_pk9_present_from_pk8.py \
  /tmp/pk8_present_openings_20.txt
python3 kryptos/generate_pk9_style_from_pk8.py \
  /tmp/pk8_style_openings_20.txt

# Calibrate the style grammar against the real PK8 answer:
cc -O3 -march=native -fopenmp kryptos/crack_pk8_q4567_crib.c \
  -o /tmp/crack_pk8_q4567_crib -lm
OMP_NUM_THREADS=32 /tmp/crack_pk8_q4567_crib \
  --all-keys /tmp/pk8_style_openings_20.txt

OMP_NUM_THREADS=32 /tmp/crack_pk9_q567_t8_crib \
  --all-keys /tmp/pk9_from_pk8_20.txt
OMP_NUM_THREADS=32 /tmp/crack_pk9_q567_t8_crib \
  --all-keys-t8-all-offsets T8_WORDS /tmp/pk9_from_pk8_20.txt
OMP_NUM_THREADS=32 /tmp/crack_pk9_q567_t8_crib \
  --all-keys-all-offsets /tmp/pk8_key_sequences_20.txt
OMP_NUM_THREADS=32 /tmp/crack_pk9_q567_t8_crib \
  --all-keys /tmp/pk8_letter_windows_20.txt
OMP_NUM_THREADS=32 /tmp/crack_pk9_q567_t8_crib \
  --all-keys-t8-all-offsets kryptos/theophilus_w8.txt \
  /tmp/pk8_letter_windows_20.txt
OMP_NUM_THREADS=32 /tmp/crack_pk9_q567_t8_crib \
  --all-keys /tmp/pk8_style_openings_20.txt
OMP_NUM_THREADS=32 /tmp/crack_pk9_q567_t8_crib \
  --all-keys-t8-all-offsets kryptos/theophilus_w8.txt \
  /tmp/pk8_style_openings_20.txt
OMP_NUM_THREADS=32 /tmp/crack_pk9_q567_t8_crib \
  --all-keys /tmp/pk8_present_openings_20.txt

# Reproduce the 30-letter natural-letter corpus and its grouped exact test:
python3 kryptos/generate_pk9_natural_letter_openings.py --length 30 \
  /tmp/pk9_natural_letter30.txt
OMP_NUM_THREADS=32 /tmp/crack_pk9_q567_t8_crib \
  --word-filter /tmp/pk9_natural_letter30.txt

# The analogous split exact test:
cc -O3 -march=native -fopenmp kryptos/crack_pk9_split_crib.c \
  -o /tmp/crack_pk9_split_crib -lm
OMP_NUM_THREADS=32 /tmp/crack_pk9_split_crib \
  --word-filter /tmp/pk9_natural_letter30.txt

# Repository-compatible QI/QII/QIII/QIV variants:
cc -std=c11 -O3 -march=native -fopenmp -Wall -Wextra -Werror \
  kryptos/break_pk9_quagmire_variants.c -o /tmp/pk9_qvariants -lm
/tmp/pk9_qvariants --self-test
OMP_NUM_THREADS=32 /tmp/pk9_qvariants
/tmp/pk9_qvariants --fixed CLOCK BERLIN KRYPTOS
```

## Post-PK8 structural searches

PK8's recovered keys reveal a one-character insertion ladder in its first three
wheels: `METE -> METER -> METIER`. The new
`break_pk9_structured.c` tests the direct PK9 analogue without using any PK9
answer material: enumerate every broad-dictionary `Q5 -> Q6 -> Q7` insertion
ladder and solve the unknown T8 block assignment by a position-aware Held-Karp
dynamic program. The forward layout uses all 143 bigrams; the inverse layout's
contiguous blocks permit exact decomposition of the full quadgram objective. It
covers 25,120 unique chains.

Four independently encrypted `IRATE -> PIRATE -> PIRATES`, T8=`LANGUAGE`
controls validate both layer orders and both layouts. Three recover all 144
plaintext letters and the T8 assignment exactly at quadgram score `-4.335694`.
For inverse-layout T8-then-Q, every 18-letter plaintext block is recovered
exactly but their best-scoring order differs: only seven boundaries depend on
the block permutation, so an n-gram model can legitimately prefer a wrong
ordering of otherwise perfect English blocks. The control checks the unordered
block multiset in that case.

The four combinations of layer order and complete-columnar orientation all
produce only noise on PK9:

| Q/T order | rectangular convention | best quadgram score |
| --- | --- | ---: |
| Q5+Q6+Q7 then T8 | canonical forward | `-6.573477` |
| T8 then Q5+Q6+Q7 | canonical forward | `-6.645079` |
| Q5+Q6+Q7 then T8 | inverse layout | `-6.621962` |
| T8 then Q5+Q6+Q7 | inverse layout | `-6.938111` |

`break_pk9_partial_ladder.c` weakens the relation further. It enumerates all
24,746 insertion-related Q5/Q6 pairs, derives an unrestricted Q7 by alternating
seven monogram fits with the exact T8 assignment, and finally quadgram-ranks the
complete plaintext. On an unrelated `IRATE/PIRATE/CAPTAIN/LANGUAGE` control,
the exact answer ranks first at `-4.335694`; rank 2 is only `-6.049330`. On PK9,
the best candidate is noise at `-6.099314`. A symmetric Q6/Q7-pair experiment,
deriving unrestricted Q5, also recovered its planted answer at rank 1 but gave
only noise on PK9 (`-6.169524`).

These controls matter: unlike earlier local word and coordinate annealers, both
structural attacks demonstrably recover their planted constructions from the
full broad search. Their negative PK9 result therefore rejects those specific
insertion relations under the tentative architecture, rather than merely
recording an optimizer failure.

Two additional exact opening corpora were tested with all 40,320 T8 assignments
and the broad Q5/Q6/Q7 dictionary filter:

- 121,468 return-journey/archive openings from
  `generate_pk9_return_openings.py`: 4,897,589,760 candidates, zero word-key
  hits;
- 6,761 short-letter openings (the literal letter mentioned at PK8's ending)
  from `generate_pk9_letter_openings.py` plus the earlier focused generator:
  272,603,520 candidates, zero word-key hits.

Every 18-letter window of the original Kryptos K1-K3 plaintexts was also tested
at every PK9 offset: 718 cribs, 91,186 placements, 3,676,619,520 candidates, and
zero full-crib or word-key hits.

## Split-layer and alternate-route searches

The structured solver now permits each of Q5, Q6, and Q7 independently on
either side of T8. It tests all eight splits under canonical forward, inverse,
and uniformly row-reversed block layouts. Twenty-four planted controls validate
the complete matrix: 22 recover the exact 144 letters and T8 assignment; the
two inverse cases in which only block-invariant Q6 is inner recover the exact
unordered set of 18-letter plaintext blocks. All 25,120 insertion chains are
noise in every model. The best result over the new row-reversed models is still
nonsense at `-6.444532`.

For the especially motivated `Q5+Q6 -> T8 -> Q7` split, suggested by PK9's raw
period-7 coincidence peak:

- all 5,275,200 insertion-chain/independent-phase combinations were tested;
  the best was noise at `-6.423793`;
- `break_pk9_partial_split.c` enumerated 24,746 Q5/Q6 insertion pairs while
  deriving unrestricted Q7 and T8; its planted answer ranked first at
  `-4.335694`, whereas PK9's best was noise at `-6.036245`;
- the complementary controlled Q6/Q7-pair scan covered 26,334 pairs and gave
  only `-6.130672` on PK9;
- moving Q6 outside T8 (`Q5 -> T8 -> Q6+Q7`) gave `-6.036951` after passing the
  same full planted scan;
- a row-reversed-T8 partial scan passed its control and gave `-6.084437`.

Literal PK8 keys `METER/METIER/MASTERY` were also tested under every split,
three route conventions, all 210 independent phase combinations, and all eight
independent sign combinations. That is 1,680 clock variants per route/split,
with the arbitrary T8 assignment solved for each. The overall best score,
`-6.611097`, is noise.

`crack_pk9_split_crib.c` is an independent exact-crib engine for
`Q5+Q6 -> T8 -> Q7`. Thirty crib letters overdetermine the 16 gauge-independent
clock coordinates. The implementation solves over GF(2) and GF(13), combines
solutions modulo 26, and explicitly enumerates all 26 affine solutions for the
few rank-15 T8 assignments. Both arbitrary-key and literal
`STEEL/SILVER/DRAWING/LANGUAGE` planted controls recover exactly.

With broad dictionary-word Q5/Q6/Q7 filters and all 40,320 T8 assignments, the
following split-layer campaigns produced no full-crib hit:

- 411,082 general narrative openings: 16,574,826,240 candidates;
- 46,101 short-letter openings: 1,858,792,320 candidates;
- 50,410 return/archive openings: 2,032,531,200 candidates;
- every 30-letter K1-K3 window at every fitting PK9 offset: 78,430 placements
  and 3,162,297,600 candidates.

The combined exact split-layer campaign covers 23,628,447,360 candidates. The
rank-deficient T8 assignments were rerun separately with their complete affine
solution sets; they also produced zero word-key or full-crib hits.

A legacy claim in `PK9_CRYPTANALYTIC_LEDGER.md` should not guide further work:
a strict rebuild and run of `solve_pk9_s7_mod13.c` returns normalized schedule
`[0,2,9,10,10,6,9]`, not the ledger's `[0,2,9,10,10,6,7]`. More importantly,
that program performs 91 independent folded-monogram choices, not an exhaustive
proof of a unique outer Q7 schedule. The claimed mod-13 invariant is therefore
neither reproduced nor evidentiary.

## Nonuniform Quagmire variants

The solved challenges consistently use Quagmire III, but treating that as
certain would make the exclusion circular. `break_pk9_quagmire_variants.c`
therefore transcribes the repository reference formulas for Quagmire I, II,
III, and IV. For fixed Q5/Q6/Q7 indicators it covers:

- all `4^3 = 64` independent layer-type triples;
- all six orders of the Q5, Q6, and Q7 layers;
- all four canonical boundaries for T8 (before all Q layers, between either
  neighboring pair, or after all Q layers);
- an exact arbitrary assignment of the eight complete-columnar blocks.

All sixteen homogeneous QI/QII/QIII/QIV controls and a deliberately mixed
QI/QII/QIV control recover the complete planted plaintext and the expected
`LANGUAGE` block assignment at score `-4.335694`. The control does not merely
recognize a supplied answer: it searches every column assignment.

The especially motivated K4-clue triple `CLOCK / BERLIN / KRYPTOS` was tested
in all 1,536 mixed models. Its best score was `-6.754026` (QIV/QI/QI, layer
order Q5/Q7/Q6, T split 1), and the text was noise. Two other fixed families
were also negative across all mixed models:

| Q5 / Q6 / Q7 | best score |
| --- | ---: |
| `CRYPT / CRYPTO / KRYPTOS` | `-6.641562` |
| `METER / METIER / MASTERY` | `-6.703272` |

Finally, the complete 25,120-chain insertion-ladder dictionary was swept under
each *homogeneous* QI, QII, QIII, and QIV family, all six Q orders, and all four
T8 boundaries: 2,411,520 chain/model combinations with an exact T assignment
for each. The best score was only `-6.452917`, for
`CRIMP / SCRIMP / SCRIMPS` under QI; its plaintext was nonsense. This excludes
an insertion ladder under those 96 homogeneous canonical models. It does not
cover all 64 mixed Q-type triples for every dictionary chain, phase-shifted
non-QIII layers, or alternate transposition routes.

## Additional natural-letter exact cribs

The earlier generated letter corpus omitted several ordinary constructions,
including “Teacher, I am sorry, I have taken one of ...” and “Master, forgive
me, I have taken one of ...”.
`generate_pk9_natural_letter_openings.py --length 30` adds grammatical
salutations, apologies, departure statements, the stolen/borrowed needle, the
ten-year wait, the archive, and farewells. It deterministically produces 33,595
distinct 30-letter prefixes.

Both exact standard-QIII engines tested every prefix against every T8
assignment with the broad Q5/Q6/Q7 dictionary filter:

| architecture | candidates | result |
| --- | ---: | --- |
| grouped `Q5+Q6+Q7 -> T8` | 1,354,550,400 | zero word-key or full-crib hits |
| split `Q5+Q6 -> T8 -> Q7` | 1,354,550,400 | zero word-key or full-crib hits |

The split campaign includes all rank-deficient assignments because its solver
already enumerates their complete affine solution sets. These are exact finite
exclusions of the generated strings, not evidence against differently worded
letters or other layer arrangements.

## Interpretation and next useful work

The dictionary filter turns a 572-million-candidate sweep from roughly five
minutes of full decryption into about fifteen seconds, and a 14-billion-state
exact test into about five and a half minutes. It makes substantially wider
crib experiments practical.

The negative results are narrow:

- although every split around T8 has now been tested for standard-QIII
  insertion-related wheels, and 96 homogeneous canonical QI–QIV models have
  been tested, the proposed Q5/Q6/Q7/T8 architecture itself is unverified;
- mixed Quagmire variants have been exhausted only for a few fixed thematic
  key triples, not for the full dictionary ladder;
- outside the explicitly unrestricted partial-ladder and PK8 bridge tests, one
  or more wheels may not be literal words in the loaded dictionaries;
- the correct plaintext may not contain the exact tested phrases;
- the correct 16- or 20-letter text may not occur in the generated grammars;
- unrestricted Q coordinates with arbitrary T8 have not been swept at every
  offset because that larger test is 389.088 billion states.

Repeating local coordinate optimization is not justified: both arbitrary-wheel
and thematic whole-word searches fail planted controls despite a large oracle
score gap. Useful continuations are broader but independently motivated exact
crib sources, or a nonlocal/exact method that couples dictionary words to the
transposition without requiring a plaintext crib.
