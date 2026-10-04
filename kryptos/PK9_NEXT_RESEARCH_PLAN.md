# PK9 Next Research Plan: the PK8 Connection

**Date:** 2026-10-02 (superseded by recovered construction 2026-10-04)
**Status:** Historical pre-recovery plan. PK9 is now independently verified as `Q3(CLEPSYDRA) → Spiral(12) → T(BEAMWORK)` by `verify_pk9_solution.py`.

## Correct interpretation of Dan's hint

PK8 is now independently verified, so PK9 should not be attacked by copying
PK8's literal wheels. The useful connection is the construction pattern:

```text
PK8 = Q4(METE) + Q5(METER) + Q6(METIER) + Q7(MASTERY)
PK9 = published hypothesis only: Q7 + Q6 + Q5 + T8
```

PK8 demonstrates an additive multi-clock construction, structured thematic
keys, and an insertion-like relationship among the first three wheel words.
It does **not** prove that PK9 uses `METER`, `METIER`, or `MASTERY`, nor that
the proposed PK9 layer order is correct.

The direct literal-key bridge has already been rejected by exhaustive tests in
`PK9_PK8_PHASE_BRIDGE_REPORT.md`. Period-7 autocorrelation and repeated
ciphertext fragments are also insufficient: planted controls show that
keyword wheels can create those effects by chance.

## First work package: structure-first wheel search

Search for PK9 wheel triples by relationship, not merely by independent word
membership:

1. insertion chains and shared stems;
2. edit distances of one to three letters;
3. thematic craft/material/pigment vocabulary;
4. an unrelated but thematically paired final wheel;
5. all gauge classes of the three-wheel sum-clock.

For each candidate triple, test both `QT` and `TQ` interpretations and all
8! width-8 column permutations. Every survivor must pass a complete
re-encryption check against the 144-character ciphertext.

## Search ordering

* **TQ:** use the ciphertext-multiset chi-square filter first. This rejects
  word-wheel triples before any transposition enumeration.
* **QT:** retain the brute-force/joint search path; the equivalent multiset
  filter is not discriminating in this order.
* **No-crib fallback:** use quadgram ranking only to prioritize candidates,
  never as proof.
* **Crib path:** continue all-offset searches only with regenerated narrative
  framings; prior negative results mostly establish that the tested crib
  corpus did not contain the opening.

## Acceptance criteria

A result is a candidate only if it supplies:

1. exact 144-character plaintext;
2. explicit wheel values, gauge choice, layer order, and transposition order;
3. encryption back to the published PK9 ciphertext, byte-for-byte;
4. readable plaintext independent of the score used to find it.

Those four criteria are now satisfied by `verify_pk9_solution.py`. This document remains a historical record of the failed local search; the recovered construction and plaintext are canonical in `pk_verified_solutions.json`. Public-solve provenance and the superseded candidates are tracked in `PK9_OFFICIAL_SOLVE_RESEARCH_2026_10_03.md`.

## First structured-triple result

The broad vocabularies produced 804 Q5/Q6/Q7 triples satisfying the
relationship filter. They were tested with the existing exact scorer under
both QT and TQ, sweeping all 40,320 width-8 transposition permutations for
each triple. No candidate crossed the scorer's language-report threshold and
no round-trip-verified plaintext was found. This is a negative result for the
relationship filter and supplied vocabulary, not evidence that PK9 has no
structured keys.

`model_pk9_key_family.py` now scores ordered-subsequence growth, multiset
inclusion, reversed/cyclic stems, shared affixes, and constant Kryptos-index
shifts. On the broad vocabulary it found 14 strongly related triples,
including `ROUGH / TROUGH / THROUGH`, `FINER / FINGER / FINGERS`, and
`TEMPE / TEMPER / TEMPERS`. Testing all 14 under both layer orders and every
T8 permutation produced no language-bearing candidate. The PK8-like relation
is therefore not sufficient by itself.

## Repository corrections

Several earlier reports in this repository used words such as “definitive,”
“proven,” or “100% resolved” for speculative PK9/PK10 scoring runs. Those
claims are superseded by the verified status in `kryptos-app/data.js` and the
session report. They must not be cited as solutions; this plan is the
canonical next-step document until a round-trip-verified break exists.
