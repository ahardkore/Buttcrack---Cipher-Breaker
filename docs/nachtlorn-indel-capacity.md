# Nachtlorn — testing one given and one taken as a raw-field repair

**R20: one insertion plus one deletion cannot repair the registered raw-field
encoding.** This is a conditional mathematical exclusion, not a recovered
message, population, or outlier.

The clue about one given and one taken could conceivably mean one insertion and
one deletion of a body letter. That is a hypothesis, not an established author
instruction. [R18](nachtlorn-field-capacity.md) excluded the unchanged body under
its raw count/key/check encoding, but insertions and deletions can change field
alignment, so the unchanged-body proof alone does not settle this repair.

## Scope and result

Before computing on the source, R20 registered the full 8,736-letter body and
exactly R18's hypothetical key-only format: 312 cells with a 7-letter count,
14-letter key and 7-letter checksum, either interleaved or field-major; A0 or
A1 positional digits; either direction; and one fixed arbitrary bijective
alphabet. These are hypothetical serializations, **not** a format attributed to
the IBLT reference. The new test is independent of the leading glyphs of the
count and checksum fields and checks only the key64 necessary condition.

The putative repair may delete and insert any letters at any positions, including
the terminal I, or act like a substitution. It preserves total length. No edit
is made to the transcript. For each layout and alphabet convention, R is the
largest number of consecutive key-leading positions on any stride-spaced run
of the original stream that contain no more than the allowed number of distinct
glyphs. Searching all source starts covers all shifts caused by the hypothetical
edits and both digit directions.

| Layout | Alphabet | Key-leader capacity | Maximum run R | Necessary paired edits | One pair? |
|---|---|---:|---:|---:|---|
| Interleaved | A0 | 8 | 17 | At least 9 | Excluded |
| Interleaved | A1 | 7 | 16 | At least 9 | Excluded |
| Field-major | A0 | 8 | 20 | At least 8 | Excluded |
| Field-major | A1 | 7 | 15 | At least 10 | Excluded |

An **edit pair** means one deletion *and* one insertion, not one total edit. The
lower bounds are necessary, not constructive: eight pairs do not imply a repair
exists. More edits, another representation or a different role for the clue are
not excluded. These bounds do not establish that the cipher contains an IBLT.

## Why the bound holds

There are N = 312 key-leading positions. For any fixed bijective alphabet, a
64-bit integer encoded in 14 base-26 letters allows at most 8 possible leading
glyphs with A0 digits, or 7 with A1 digits. This uses a conservative
nonnegative-suffix bound, so it is necessary even if the other digits are chosen
to be as small as possible.

With m inserted and m deleted letters, at most m target key leaders were
inserted. All other key leaders are copied from the source. The at most 2m edit
events partition the alignment into at most **2m + 1** constant-displacement
runs. Within each run, copied key leaders come from consecutive source positions
spaced by 28 (interleaved) or 14 (field-major). Since every valid leader must
belong to the same allowed glyph set, each run has at most R leaders. Thus any
valid repair must satisfy

```text
312 - m <= (2m + 1) R.
```

For the most permissive profile R = 20, one pair could account for at most
1 + 3 × 20 = 61 leaders, far short of 312. Solving the inequality gives the
listed lower bounds. All possible alphabet assignments are covered by using
*distinct-glyph counts*, rather than trying chosen alphabets.

The recorded longest-run witnesses are zero-based **letter-stream positions**;
the report records their start, end and glyph set. They establish that the
maximum is attained. Independently checking every start until its distinct-glyph
limit is exceeded establishes that no longer run was missed.

## Controls and provenance

- [Registered design and outcome](data/nachtlorn-reset-plan.json)
- [Machine-readable results and witnesses](data/nachtlorn-reset-indel-capacity-results.json)
- [Probe](../scripts/nachtlorn_indel_capacity.py) and
  [independent/synthetic tests](../tests/test_nachtlorn_indel_capacity.py)

Eight tests include exhaustive small-alphabet single-pair edits, exhaustive
comparison against a separate brute-force maximum-run implementation, a valid
synthetic full-sized raw field stream damaged by a known insertion/deletion and
reconstructed, numerical capacity checks, tampered witness rejection and an
independent replay of the original-stream certificates. Synthetic valid fields
are a capacity control, **not** a validated IBLT.

All **281 tests across 32 research modules passed** locally, with previous
optional dependencies installed; whole-repository Ruff passed. R20 itself uses
only the Python standard library. No source solver, alphabet-permutation search,
edit-pair search or chosen-word scoring was run. The earlier packed-object and
R18 work already used the capacity principle; the contribution here is the
phase-changing indel bound, not a new underlying encoding principle.

The source gist was refreshed on 2026-11-02: one revision, zero comments, one
untruncated 11,129-byte file with SHA256
`04eddf97e8ebbc9ce2565269508d63c99b60efc7cacf3f2c020f14215dc67e7e`,
matching the local transcript. No new author material was found.

```bash
python3 scripts/nachtlorn_indel_capacity.py docs/data/nachtlorn-transcript.txt \
  --output scratch/nachtlorn-r20-replay.json
python3 -m unittest tests.test_nachtlorn_indel_capacity -v
```

## Interpretation

This closes only the proposed *one-pair raw-field repair*. It does not rule out
one given/taken at the level of actual decoded objects, or another interpretation
of the poem. The visual-strip hypothesis still needs an independent anchor, and
[R16/R17 full-body gzip cases remain UNKNOWN](nachtlorn-stored-gzip.md). The
construction → actual population → independently justified outlier bridge remains
unresolved.
