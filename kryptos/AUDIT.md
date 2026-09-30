# Audit of the PK records, 2026-09-30

Every stored record was re-checked against its ciphertext. The test is
mechanical: does the key a record names turn the plaintext it stores back into
the published ciphertext?

```console
$ python3 kryptos/verify_pk_records.py
```

It exits non-zero if anything labelled solved fails, and
`tests/test_kryptos_records.py` keeps it that way.

## Verdicts

| | verdict | evidence |
| --- | --- | --- |
| PK1 | verified | Quagmire III with `PROVENANCE` re-encrypts exactly |
| PK2 | verified | columnar width 7, order `[1,3,4,0,5,2,6]` |
| PK3 | verified | sum-clock `PENTIMENTO`/10 + `ORDINATE`/8 |
| PK4 | key not reproducible | plaintext scores -4.18; no convention rebuilds the ciphertext |
| PK5 | mechanism refuted | see below |
| PK6 | verified | double columnar width 9, then Quagmire III `PORTAL` |
| PK7 | verified, after correction | old record refuted; `ANNEAL` + `ALCHEMIST` re-encrypts exactly |
| PK8 | not a solution | stored candidate scores -6.43 and is not English |
| PK9 | unsolved | no plaintext; best stored reading -4.93 |
| PK10 | unsolved | best stored readings -6.2 to -6.6 |

Scores are quadgram fitness in log10 per character. English averages about
-4.3, and the five verified plaintexts fall between -4.2 and -4.45.

## PK7 was fabricated

The old record paired the ciphertext with a passage beginning
"HEPOINTEDTOTHEHEARTH". It fails on its own terms. Three ciphertext blocks are
identical (`HTE` at blocks 51, 55 and 91, all at the same phase) but the record
maps them to three different plaintext trigrams: `MET`, `ENT`, `FOR`. No
composition of a period-6 substitution with a 3-letter block cipher can do
that, in either order.

The real plaintext was recovered from the ciphertext alone. See [PK7.md](PK7.md).

## PK5's stated mechanism cannot produce its plaintext

The record says "columnar transposition, then Quagmire III with period 17".
Under that order each ciphertext residue class is a rotation of a subset of the
plaintext's letters, so some choice of 17 shifts has to make the classes add up
to the plaintext's letter multiset. No such choice exists. The argument never
uses the transposition, so no column order rescues it. Either the plaintext or
the mechanism is wrong. The plaintext is coherent and fits the narrative, so it
is kept, with the key claim withdrawn.

## PK4's key is under-specified

"Dual-Clock Substitution p5 + p9, Transposition Width 8" names neither the
wheels nor the column order. Every columnar convention at widths 8 and 28 was
searched against the stored plaintext, with the keystream phased from either
side and over both the KRYPTOS and plain alphabets. None rebuilds the
ciphertext. The plaintext is neither confirmed nor refuted.

## PK8 was never solved here

PK8 was solved by Kevin Hu and the key was not published. This directory stored
a four-wheel candidate as `plaintext`, with the status "SOLVED (SEALED IN
CUSTODY)". The candidate is internally consistent, in that the clock parameters
it names do produce it from the ciphertext, but it is not English: -6.43 log10
per character, and 8% coverage in words of four letters or more.

The "71.2% lexical word coverage" reported alongside it counted two- and
three-letter fragments of a Viterbi segmentation (`nr`, `hp`, `xx`, `oe`), a
statistic that random letters also score well on. The candidate is kept,
labelled as a failed attempt.

## PK9 and PK10 claimed confidence they had not earned

"UNSOLVED EMPIRICAL FRONTIER (100% MATHEMATICALLY LOCKED)" described search
space that had been eliminated, not a recovered key. Both are now recorded as
unsolved. The stored PK10 readings score -6.2 to -6.6 and are not English.

## The verification tooling was not verifying

`test_full_suite_reproducibility.py` printed "0 / 11 TESTS PASSED (100%
SUCCESS)". The success string was hardcoded, and every module failed anyway
because the script resolved its paths against the caller's working directory
while the README told you to run it from the repository root. The percentage
is now computed, paths are anchored to the script, the exit status is non-zero
on failure, and record verification runs as its first module.

Most of its modules re-run an analysis script and check that it still prints
its own conclusion. That is a regression test, not evidence, and the file now
says so.

`verify_all_mathematical_theorems.py` printed "100% PROVEN" for arithmetic on
quantities chosen after the fact. The GPS section sums four selected letters to
reach 57, then takes a different selected sum modulo 60 to reach 6. Nothing
there was used to break a cipher. The file now carries a header saying as much.

## What is genuinely solved

PK1, PK2, PK3, PK6 and PK7 reproduce their ciphertexts from their stated keys.
Of those, the solver recovers PK1, PK2, PK3 and PK7 from ciphertext alone.
