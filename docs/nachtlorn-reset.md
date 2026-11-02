# Nachtlorn — reset record

**Reset begun; no solution claimed.**


**Latest continuation:** [whole-packet stored-gzip constraints](nachtlorn-stored-gzip.md)
exclude five length/convention cases by exact trailer arithmetic. The two full-body
cases time out under both Z3 and an independently budgeted cvc5 cross-check.
Neither solver produces a source candidate: no actual-source CRC check is reached.
The drop-final-I exclusions apply only to this narrow gzip construction; no packet,
population, final outlier or general gzip exclusion is established.

**Earlier continuation:** [little-endian congruence checks](nachtlorn-little-endian-invariants.md)
produce header-compatible gzip/zlib/XZ alphabets in all four numeral/final-I models,
but no verified complete packet among the 12 arbitrary witnesses and 96 bounded
zero-restoration checks. Four bzip2 feasibility queries time out and remain UNKNOWN.
This does not extend the earlier big-endian exclusions to the other byte order.

**Earlier continuation:** [exact representation invariants](nachtlorn-prefix-invariants.md)
exclude raw big-endian whole-base26 gzip, bzip2 and XZ under **every** digit-alphabet
permutation, both numeral conventions and full/drop-final-I inputs. An independent
six-glyph certificate verifies the exclusions. Zlib headers remain underdetermined;
no complete packet, recovered population or final outlier is established.

**Earlier continuation:** [replacement-role assessment](nachtlorn-replacement-roles.md)
separates literal **BLACK/GREEN/WHITE** keys, keyword digit alphabets and eight
exact book addresses. All registered recovery gates remain negative. The book
association is not a confirmed payload key or an answer class.

**Earlier continuation:** [fieldwise tables and poem-key checks](nachtlorn-fieldwise-and-poem-keys.md)
test the independent field encoding and the explicit **GLPNM/WLPNM** unit-shift
hypothesis. Both fail their bounded recovery gates; direct byte-XOR roles also
recover no packet. No population or final outlier is claimed.

**Earlier continuation:** the [colour/signed-cell assessment](nachtlorn-colour-continuation.md)
records a black-bowl/**mourning** passage that preserves **BLOOM**, negative
WLOOM key tests, and a negative signed-count-stripe preflight. No object population
or final outlier is established; GLOOM is not privileged by being an English word.

**Earlier colour hypothesis:** the user-proposed blue replacement gives a book-grounded
**green → GLOOM** reading. The [colour assessment](nachtlorn-colour-hypothesis.md)
distinguishes this contextual lead from the completed, negative bounded key tests.

**Continuation:** the [role assessment](nachtlorn-reset-role-assessment.md) now
records completed, answer-blind reference/schema/running-key checks. The supported
reference association has not been promoted to a cipher key or an answer class.
 The user correctly identified that earlier
short word matches were anchoring the investigation after additional information
about construction and interpretation layers had arrived.

## What changed

- The [active ledger](nachtlorn-clue-ledger.md) is now facts-first. The previous
  ledger is [archived verbatim](nachtlorn-pre-reset-ledger.md), not silently
  rewritten or deleted.
- Historical candidate words, modified keys, rosters, phrase repairs and matching
  coordinates cannot select a model or validate a result. Reconsideration requires
  an independently specified construction and outlier rule.
- The acrostic remains a literal observation. Its role is unassigned.
- The indentation seed remains a verified formatting parameter. The book lookup
  is an external association, not an established meaning or a required answer class.
- The author describes interconnected stages, including construction and
  interpretation. A stack of four/five ciphers is not the default model.
- Prior bounded negatives stay in the historical log so unchanged work is not
  repeated. Failing one family does not justify adding another arbitrary layer.

## First concrete check: forward construction, not word recovery

A fresh, independent-of-fragments audit reproduced the complete body layout from
its unmodified letters with only these rules:

```text
row width       60 letters
printed groups   5 letters
indent RNG      random.Random(4300)
indent draw     randrange(8), once per row
line ending     LF
```

This reproduces **all body spaces and line breaks byte for byte**. Adding the
literal original preamble reproduces the complete 11,129-byte file. No letters
were added, removed or changed. This sharpens the previously known indentation
fit into an explicit, tested **layout-only forward model**; it is not new evidence
that the body has been decrypted.

Two consequences matter for the reset:

1. The single-letter last group does not require a padding operation to explain
   its presentation. Its special meaning, if any, is still an open question.
2. Matching the layout does not identify the letter generator, prove a literary
   reading, or eliminate a deliberate alignment involving the letters themselves.

The tests deliberately show that changing the body letters can preserve a perfect
layout fit, while changing a space or line ending breaks that fit. This makes the
limit of the result explicit.

## Next gate, before another body search

The next task is to distinguish the acrostic/seed's possible roles: literal key
or instruction, reference or identifier, or named construction. Each admitted
model must state its clue basis, object type, parameters, forward prediction,
inverse where applicable, and outlier rule before inspecting an answer string.
A short recognizable output is not that prediction.

The user's original-row vertical-strip model is retained as a separate hypothesis.
It must use one original row per strip and actual letter counts, with a zero/anchor
justified independently of any old candidate. It must not be replaced by pooled
page statistics or by searching many guides until a familiar word is selected.

This turn establishes the clean baseline and operating rules; it does **not**
launch another encryption grid or assign a new meaning to each poem line.

## Reproducibility

- [Facts-only result](data/nachtlorn-reset-facts.json)
- [Machine-readable reset plan](data/nachtlorn-reset-plan.json)
- [Facts-only script](../scripts/nachtlorn_reset_audit.py)
- [Reset tests](../tests/test_nachtlorn_reset_audit.py)

```bash
python3 scripts/nachtlorn_reset_audit.py docs/data/nachtlorn-transcript.txt
python3 -m unittest tests.test_nachtlorn_reset_audit
```

Historical regression tests still reproduce earlier arithmetic for archival
consistency; they are not validation of a new model or answer. The reset audit
and its tests are separate and candidate-free.

Nine reset tests pass, including an independent scalar formatting oracle,
whitespace-mutation checks, unchanged global RNG state and source overwrite
protection. The source bytes and their original SHA256 are unchanged.
