# Nachtlorn — the other byte order remains underdetermined

**Status: unresolved. No plaintext, recovered population, or final outlier.**


**Follow-up:** [R16/R17 complete stored-gzip constraints](nachtlorn-stored-gzip.md)
add both-end packet structure and independent CRC validation to one narrow gzip
class. Five cases are excluded by the trailer interval; two remain UNKNOWN under
two solvers. No source candidate or source CRC check is reached.

R15 tests the little-endian counterpart explicitly left open by
[R14's big-endian exclusion](nachtlorn-prefix-invariants.md). The two byte orders
must not be conflated: excluding three formats in one does not exclude them in
the other, or establish that the other byte order was actually used.

## Result

Each SAT entry means **at least one admitted header** is achievable by an
arbitrary digit alphabet. It does not mean every header alternative is feasible,
or that the bytes constitute that file format.

| Literal-body model | gzip header | zlib header | bzip2 header | XZ header |
|---|---|---|---|---|
| Full 8,736 letters, digits 0–25 | SAT | SAT | Unknown: timeout | SAT |
| Full 8,736 letters, digits 1–26 | SAT | SAT | Unknown: timeout | SAT |
| Explicit final-I removal, digits 0–25 | SAT | SAT | Unknown: timeout | SAT |
| Explicit final-I removal, digits 1–26 | SAT | SAT | Unknown: timeout | SAT |

Of **16 registered feasibility queries**, 12 returned SAT, four returned
UNKNOWN due to the solver's time limit, and none returned UNSAT.

Every SAT witness was checked in ordinary Python for a full bijection, the
claimed header, the actual minimal byte representation, and exact retained-letter
roundtrip. The published witnesses can be verified without installing or rerunning
the solver. Different arbitrary alphabets can force different formats' headers
onto the same original body; they are not a recovered common key.

Each of the 12 witnesses was then tested for a complete, checksum-validated
compressed stream, with 0–7 restored trailing zero bytes: **96 bounded packet
checks, zero verified complete streams**. This rejects only those arbitrary
completions under the validation limits. It does not reject all header-compatible
alphabets, prove the data uncompressed, or establish a role for the final I.

The four bzip2 timeouts are **unresolved feasibility**, not mathematical exclusions.
No alphabet counts or exhaustive search of satisfying maps are claimed.

[Machine-readable results](data/nachtlorn-reset-little-endian-results.json)
include the solver version, parameters, formula fingerprints, statuses, timeout
reasons, independently verifiable witnesses and bounded packet-check results.

## Why the end of the numeral now matters

For minimal little-endian bytes, the first `m` bytes specify a residue:

```text
N mod 2**(8*m) = int.from_bytes(header, 'little')
```

Let each glyph have an unknown digit `d` in 0–25 and add bias 0 or 1. Then:

```text
N = sum((d[glyph] + bias) * 26**position_from_right)
```

Because 26 is even, positions at least `8*m` from the right contribute zero to
this residue. Thus a six-byte XZ magic constrains at most the last **48 numeral
letters**, not the first six letters used in the big-endian contradiction.
For the full source, the other 8,688 letters contribute no bits to that particular
header residue. They still matter to the actual packet, which is why checking a
complete stream is a much stronger requirement.

The solver assigns 26 distinct digits in 0–25, applies the bias explicitly, and
requires the residue to match one of the admitted headers. A numeric-length
condition prevents a short integer from falsely matching a header whose trailing
high-order zero byte would be absent from minimal bytes. For the actual long
source, its numeric lower bound already guarantees sufficient byte length.

This is an existential feasibility test, not a count of alphabets and not a
cipher-identification score. A SAT result is independently checkable. An UNKNOWN
result says nothing about existence or nonexistence.

## Registered scope and budgets

The [R15 plan](data/nachtlorn-reset-plan.json) was recorded before the source run.

- Original glyph order; full body and explicitly labelled final-I removal.
- Arbitrary bijection to digits 0–25 or 1–26; zero-leading A0 numeral allowed
  conservatively, with canonical/noncanonical status recorded per witness.
- One whole integer, minimal **little-endian** bytes.
- Exactly the R14 catalog: 32 legal gzip flag prefixes, 66 valid zlib headers,
  18 bzip2 first-block/empty-stream prefixes and the six-byte XZ magic.
- One disjunction per family/model: 16 queries, one witness per SAT query.
- Z3 **5.3.3**, package `z3-solver==5.3.3.0`; seed 4300; **15,000 ms per query**.
  This is a solver soft timeout, not an exact wall-clock cutoff; the recorded
  timeout queries took about 15–16 seconds each.
- For a SAT witness only, bounded decompression: output cap 1 MiB, XZ memory
  cap 64 MiB, no supplied preset dictionary, valid checksum/EOF and consumption
  of the entire restored packet required.

Restoring trailing zeros is important: converting a gzip member to a
little-endian integer can discard zero bytes from its length trailer. The 0–7
restoration range was registered before this source run and matches earlier
whole-integer research conventions. It does not alter a header already inside
the long minimal representation. No bytes are restored or changed in the source.

No reversed numeral digits, block packing, extra letter cipher, arbitrary offsets,
passwords, book transformation, favourite word, or candidate population is added.
The optional solver is installed only in ignored scratch storage; application
dependencies are unchanged.

## Controls

Twelve tests pass with the optional solver installed:

- modular coefficients versus independent full-integer arithmetic, including odd
  and even synthetic bases, both biases and modulus widths up to 80 bits;
- source-prefix changes leaving the low 80 bits unchanged when the suffix is held;
- exact fixed-width roundtrip including zero-leading glyphs;
- SAT/UNSAT comparisons with exhaustive small-alphabet permutations;
- the short-header/minimal-byte-length trap;
- known relabelled gzip, zlib, bzip2 and XZ controls under both biases, recovering
  their complete original compressed packets and payload hashes;
- mocked timeout classification that remains UNKNOWN and never requests a model;
- missing-solver errors rather than false negative results;
- independent verification of every published SAT witness and its packet checks;
- source-overwrite and invalid-timeout protection.

Without the optional solver, the seven standard-library tests—including published
witness verification—still pass; five solver-dependent tests are explicitly
skipped, never counted as negative feasibility results.

Broader regression: **229 focused research tests across 27 modules pass**, with
the optional solver and existing PyCryptodome research dependency available
(25.375 seconds). Ruff passes. Working-tree syntax/link auditing covers **484
Python sources and 72 Markdown files**, including the new files, with no defects.
The full application-wide suite was not rerun in this pass.

## Reproduce

```bash
python3 -m pip install --target scratch/nachtlorn-smt-deps z3-solver==5.3.3.0
export PYTHONPATH="$PWD/scratch/nachtlorn-smt-deps${PYTHONPATH:+:$PYTHONPATH}"
python3 -m unittest tests.test_nachtlorn_little_endian_probe -v
python3 scripts/nachtlorn_little_endian_probe.py docs/data/nachtlorn-transcript.txt \
  --output docs/data/nachtlorn-reset-little-endian-results.json
```

Elapsed times are not deterministic; bounded solver results can also vary by
version or hardware. The reproducible certificates are the SAT mappings and
ordinary-Python checks. A rerun that solves a previously timed-out query would
be additional evidence, not a contradiction of its earlier UNKNOWN status.

The source remains 11,129 bytes, SHA256
`04eddf97e8ebbc9ce2565269508d63c99b60efc7cacf3f2c020f14215dc67e7e`.

## Decision

The R14 exclusions remain valid in their **big-endian** scope. They cannot be
extended to little-endian gzip or XZ, for which explicit header-compatible maps
now exist. Zlib headers remain underdetermined in both byte orders, and the
little-endian bzip2 feasibility question remains open at the registered budget.

Do not promote any witness alphabet to a key, or select a byte order merely
because a header can be manufactured. A defensible next recovery gate needs
whole-stream structure or an independently justified alphabet/construction that
constrains the rest of the body. Merely enumerating more header-only witnesses
would not provide that missing validation. No semantic encryption layer or final
outlier is inferred from these results.
