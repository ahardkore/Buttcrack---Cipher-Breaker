# PK9 / PK8 Global-Phase Bridge Test

**Date:** 2026-10-01  
**Target:** Paradigm Kryptos PK9 (`N = 144`)  
**Result:** no solution under the tested finite PK8-reuse family

## Question

PK8's verified Quagmire III wheels of lengths 5, 6, and 7 are:

```text
Q5 = METER
Q6 = METIER
Q7 = MASTERY
```

Earlier bridge work tested literal reuse with independent wheel rotations and reversals. This test extends that family by allowing one common KRYPTOS-index offset after the three wheels are summed. It models a possible global indicator/alphabet alignment change without changing the relative pattern of the three PK8 wheels.

For every candidate, the test evaluates both layer orders:

```text
Q5 + Q6 + Q7 -> complete T8
complete T8 -> Q5 + Q6 + Q7
```

Here `T8` is a complete 18-row, 8-column transposition. Every one of its `8! = 40,320` column assignments is enumerated.

## Exact finite search space

For each layer order, the search consists of:

- 5 rotations and 2 orientations of `METER`;
- 6 rotations and 2 orientations of `METIER`;
- 7 rotations and 2 orientations of `MASTERY`;
- 26 common additive offsets in KRYPTOS-index space;
- all 40,320 width-8 complete-columnar assignments.

That is:

```text
26 × (5 × 2) × (6 × 2) × (7 × 2) = 43,680 wheel variants
43,680 × 40,320 = 1,761,177,600 candidates per layer order
3,522,355,200 total scored candidates
```

`test_pk8_pk9_transformed_keys.c` scores each complete decrypted text with the repository English quadgram table. Its self-test encrypts a 144-character control with nonzero phases, reversals, a nonzero common offset, and a known T8 assignment; the implementation's exact known-key/control round trip recovers the control exactly.

## Result

The 32-thread run completed in `713.021 s`.

| Layer order | Best quadgram score per character | Interpretation |
| --- | ---: | --- |
| `Q5+Q6+Q7 -> T8` | `-6.579653` | noise / no readable plaintext |
| `T8 -> Q5+Q6+Q7` | `-6.662095` | noise / no readable plaintext |

For calibration, the same scorer gives the synthetic control `-4.371733` and the verified PK8 plaintext `-4.361308` per character. Neither PK9 result is close to that range, and neither top text has coherent language.

## Scope and conclusion

This is a **negative result for a narrow hypothesis**, not a proof about PK9 generally. It rules out the specified direct PK8 wheel-reuse family under standard Quagmire III over the KRYPTOS alphabet, a common 0–25 index offset, the tested rotations/reflections, either side of a complete width-8 transposition, and every complete-columnar assignment.

It does **not** rule out different PK9 wheels, a non-common wheel transformation, another Quagmire type/alphabet, an additional layer, a non-columnar route, or an entirely different construction. It produces no plaintext and should not be represented as a break.

## Reproduction

From the repository root:

```bash
cc -O3 -march=native -fopenmp -Wall -Wextra -Werror \
  kryptos/test_pk8_pk9_transformed_keys.c \
  -o /tmp/test_pk8_pk9_transformed_keys -lm

/tmp/test_pk8_pk9_transformed_keys --self-test
OMP_NUM_THREADS=32 /tmp/test_pk8_pk9_transformed_keys
```
