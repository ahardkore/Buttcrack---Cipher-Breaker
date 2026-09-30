# Audit of the Paradigm Kryptos records (2026-09-30)

Every claim in this directory was re-checked against the ciphertexts. The test
is mechanical and has one question: **does the key a record names turn the
plaintext it stores back into the published ciphertext?** Run it yourself:

```console
$ python3 kryptos/verify_pk_records.py
```

It exits non-zero if any record labelled SOLVED fails, and it is wired into
`tests/test_kryptos_records.py` so CI keeps it honest.

## Verdicts

| challenge | verdict | stored status now | evidence |
| --- | --- | --- | --- |
| PK1 | **verified** | SOLVED (VERIFIED) | Quagmire III / `PROVENANCE` re-encrypts exactly |
| PK2 | **verified** | SOLVED (VERIFIED) | columnar width 7, order `[1,3,4,0,5,2,6]`, re-encrypts exactly |
| PK3 | **verified** | SOLVED (VERIFIED) | sum-clock `PENTIMENTO`/10 + `ORDINATE`/8 re-encrypts exactly |
| PK4 | key not reproducible | PLAINTEXT ONLY | plaintext is English (−4.18); no convention reproduces the ciphertext |
| PK5 | key **refuted** | PLAINTEXT ONLY | the stated order is impossible for this plaintext (see below) |
| PK6 | **verified** | SOLVED (VERIFIED) | double columnar + Quagmire III `PORTAL` re-encrypts exactly |
| PK7 | **verified** (corrected) | SOLVED (VERIFIED) | old record refuted; new key `ANNEAL` + `ALCHEMIST` re-encrypts exactly |
| PK8 | not a solution | UNSOLVED HERE | stored candidate is not English (−6.43, 8% words) |
| PK9 | unsolved | UNSOLVED | no plaintext; best reading −4.93 |
| PK10 | unsolved | UNSOLVED | best readings −6.2 to −6.6; not English |

Fitness is quadgram log10 per character: real English averages −4.3, and the
five verified PK plaintexts sit between −4.2 and −4.45.

## What was wrong, and how it was caught

**PK7 was fabricated.** The old record paired the ciphertext with
"HEPOINTEDTOTHEHEARTH…". Three identical ciphertext blocks (`HTE` at blocks
51, 55 and 91, all at the same phase) were mapped to three *different*
plaintext trigrams — impossible for any composition of a period-6 substitution
with a 3-letter block cipher, in either order. The real plaintext was
recovered from ciphertext alone; see [`PK7_BREAK.md`](PK7_BREAK.md).

**PK5's stated mechanism is refuted for its stored plaintext.** Under
"transposition, then a period-17 Quagmire III", each ciphertext residue class
is a rotation of a subset of the plaintext's letters. No assignment of 17
shifts makes the classes add up to this plaintext's letter multiset — and that
holds whatever the transposition is, since the argument never uses it. Either
the plaintext or the mechanism is wrong; the plaintext itself is coherent
English and consistent with the narrative, so it is retained but demoted.

**PK4's key is under-specified.** "Dual-Clock Substitution p5 + p9,
Transposition Width 8" does not name the wheels or the column order. Every
columnar convention at widths 8 and 28, with the keystream phased from either
side and over both the KRYPTOS and plain alphabets, was searched against the
stored plaintext. None reproduces the ciphertext. The plaintext is neither
confirmed nor refuted.

**PK8 was never solved here.** It was solved externally by Kevin Hu and the key
was not published. The record stored a four-wheel candidate as `plaintext` with
the status "SOLVED (SEALED IN CUSTODY)". The candidate *is* internally
consistent — the clock parameters it names do produce it from the ciphertext —
but the output is not English: −6.43 log10/char and 8% coverage in words of
four letters or more. The "71.2% lexical word coverage" previously reported
counted two- and three-letter fragments of a Viterbi segmentation (`nr`, `hp`,
`xx`, `oe`, …), a statistic random letters also score well on.

**PK9/PK10 were labelled with confidence they had not earned.** "UNSOLVED
EMPIRICAL FRONTIER (100% MATHEMATICALLY LOCKED)" described eliminated search
space, not a recovered key. Both are now plainly UNSOLVED. The stored PK10
readings score −6.2 to −6.6 and are not English.

## The "verification" tooling was not verifying

* `test_full_suite_reproducibility.py` printed **"0 / 11 TESTS PASSED (100%
  SUCCESS)"** — the success string was hardcoded — and every module failed
  anyway because the script resolves its paths against the working directory
  while the README tells you to run it from the repository root. Both are
  fixed: the percentage is computed, paths resolve against the script, the exit
  status is non-zero on failure, and the record verification above runs as the
  first module.
* Most of its modules check that an analysis script still prints its own
  conclusion. That is a regression test, not evidence. The suite now says so.
* `verify_all_mathematical_theorems.py` prints "100% PROVEN" for what are
  numerical observations about hand-picked quantities — the GPS "theorem" sums
  four chosen letters to 57, then takes another chosen sum mod 60 to reach 6.
  Nothing there was used to break a cipher, and the file now carries a header
  saying as much.

## What is genuinely solved here

PK1, PK2, PK3, PK6 and PK7 — five of the ten — reproduce their ciphertexts
from their stated keys. `scripts/kryptos_ctf.py` additionally shows which of
them the solver can recover with no hints at all: PK1, PK2, PK3 and PK7.
