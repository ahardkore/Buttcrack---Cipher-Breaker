# PK8 Structured Ciphertext-Only Break

**Date:** 2026-10-01

**Result:** exact PK8 keys and plaintext recovered at rank 1 from the ciphertext

## Scope and honesty boundary

`break_pk8_structured.c` is a retrospective, answer-free executable attack. Its
source contains neither PK8's plaintext nor any of its four keys. Given only the
official ciphertext, the established `Q(4)Q(5)Q(6)Q(7)` architecture, broad
repository dictionaries, and a concrete interpretation of the public clue that
the key has "quite a lot of entropy, but some structure," it recovers the exact
answer.

The insertion-ladder interpretation was developed after PK8's solution became
public. Therefore this is a reproducible ciphertext-only recovery method and a
useful cryptanalytic result, but it is not a claim of independent priority or
evidence that the structural hypothesis would necessarily have been found
before publication.

## Algebra

All four layers are Quagmire III over the same KRYPTOS alphabet. Sequential
layers therefore collapse to addition in that alphabet's index space:

```text
C[i] = P[i] + Q4[i mod 4] + Q5[i mod 5]
             + Q6[i mod 6] + Q7[i mod 7]  (mod 26)
```

The public clue says the algorithm is simple and the key has high entropy with
some structure. The tested structural interpretation is:

1. Q4, Q5, and Q6 are dictionary words;
2. deleting one character from Q6 yields Q5;
3. deleting one character from Q5 yields Q4;
4. Q7 is unrestricted and recovered statistically.

The broad local dictionaries contain 7,187 unique four-letter words, 15,922
five-letter words, and 29,874 six-letter words. Deletion joins reduce their
nominal Cartesian product to only **41,371 insertion chains**.

For each chain, subtract Q4, Q5, and Q6 from the ciphertext. The remainder is a
period-7 Quagmire shift over plaintext. Each of its seven columns contains about
22 letters, enough to test all 26 shifts by English monogram chi-square. This
derives all seven Q7 coordinates without requiring Q7 to occur in a dictionary.
The resulting complete plaintext is ranked by English quadgrams.

## Result

On the real ciphertext with 32 OpenMP threads:

```text
dictionary words: len4=7187 len5=15922 len6=29874
insertion_chains=41371 elapsed=0.201s

#1 score=-4.361307 keys=METE/METER/METIER/MASTERY
plaintext=ILEAVEATMIDNIGHTBEFOREGOINGIPICKUPONENEEDLEFROMTHEGUTTERIAMGRATEFULTOMYTEACHERBUTTHEARCHIVEISMYTRUECALLINGANDTHEKNOTAWAITSILEAVETHEWHITESMITHASHORTLETTER

#2 score=-6.475130 keys=WILE/WILED/WILLED/HQZMJOR
```

The correct plaintext is rank 1 with a `2.113823` log-score-per-character lead
over rank 2. The first three recovered words satisfy the insertion ladder
exactly:

```text
METE -> METER     (insert R)
METER -> METIER   (insert I)
```

The independently derived seven coordinates spell `MASTERY`. No PK8 crib,
plaintext fragment, or known key is consulted by the attack.

## Independent synthetic control

`--self-test` uses unrelated keys and plaintext:

```text
RATE -> IRATE -> PIRATE
Q7 = CAPTAIN
```

It encrypts a 153-letter control internally, derives `CAPTAIN` by the same seven
chi-square searches, and recovers the complete plaintext exactly.

## Reproduction

From the repository root:

```bash
cc -O3 -march=native -fopenmp -Wall -Wextra -Werror \
  kryptos/break_pk8_structured.c -o /tmp/break_pk8_structured -lm

/tmp/break_pk8_structured --self-test
OMP_NUM_THREADS=32 /tmp/break_pk8_structured
```

Expected control line:

```text
self_test_exact=PASS q4=RATE q5=IRATE q6=PIRATE q7=CAPTAIN
```

## Implication for PK9

This explains a practical route through PK8's apparently unsearchable
18-effective-coordinate clock: exploit structure before language scoring, then
derive the final wheel column by column. It also sharpens the PK8/PK9 question.
If PK9 has an analogous structured relation among its Q5/Q6/Q7 words and T8
key, searching that relation may be more productive than free-coordinate
annealing or additional unconstrained crib generation.
