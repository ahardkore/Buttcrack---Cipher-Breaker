# kryptos

Ciphertexts, solutions and working notes for the Kryptos sculpture (K1-K4) and
Dan Robinson's Paradigm Kryptos CTF (PK1-PK10).

Everything here is either a record that can be checked against a ciphertext, or
notes on attacks that were tried. The records were audited on 2026-09-30 after
one of them turned out to be wrong; see [AUDIT.md](AUDIT.md).

## Status

| | cipher | status |
| --- | --- | --- |
| PK1 | Quagmire III, KRYPTOS alphabet, period 10 (`PROVENANCE`) | solved, key verified |
| PK2 | complete columnar, width 7 | solved, key verified |
| PK3 | sum-clock, wheels of 10 and 8 (`PENTIMENTO` + `ORDINATE`) | solved, key verified |
| PK4 | columnar plus a dual-clock substitution | plaintext only, key not reproducible |
| PK5 | columnar plus Quagmire III | plaintext only, stated mechanism refuted |
| PK6 | double columnar, then Quagmire III (`PORTAL`) | solved, key verified |
| PK7 | Quagmire III (`ANNEAL`), then Hill 3x3 (`ALCHEMIST`) | solved, key verified ([PK7.md](PK7.md)) |
| PK8 | additive 4-clock over the KRYPTOS alphabet | unsolved here; solved externally, key unpublished |
| PK9 | substitution over a double columnar | unsolved ([PK8-PK10.md](PK8-PK10.md)) |
| PK10 | 3-clock over a transposition | unsolved |

"Key verified" means the key the record names re-encrypts the stored plaintext
into the published ciphertext, character for character:

```console
$ python3 kryptos/verify_pk_records.py
```

That check exits non-zero if any record labelled solved fails it, and
`tests/test_kryptos_records.py` runs it in CI.

## Files

| file | what it is |
| --- | --- |
| `pk_all_ciphertexts.json` | the ten published ciphertexts |
| `pk_verified_solutions.json` | plaintexts, keys and audit verdicts for PK1-PK7 |
| `pk_submission_manifest.json` | the same records plus the unsolved three |
| `pk_audit.json` | the audit verdicts, used by the manifest generators |
| `verify_pk_records.py` | the verification harness |
| `AUDIT.md` | what was checked and what failed |
| `PK7.md` | how PK7 was broken |
| `PK8-PK10.md` | notes on the three unsolved challenges |
| `K1-K4.md` | the sculpture's four passages |

The rest of the directory (roughly 700 Python and C files) is exploratory
attack code written while working on PK8-PK10. It is kept because the negative
results are worth something, but it is scratch work: undocumented, uneven, and
in places superseded by `PK8-PK10.md`. Nothing in the package depends on it.

## Solver scorecard

`scripts/kryptos_ctf.py` runs the solver against the corpus with no hints and
reports which published plaintexts it reproduces. As of the audit: PK1, PK2,
PK3 and PK7.
