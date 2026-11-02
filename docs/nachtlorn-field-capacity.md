# Nachtlorn — fixed-width fields fail under every digit alphabet

**R18: exact representation exclusions; cipher still unresolved.** No plaintext,
recovered object population or final outlier is claimed.

The earlier [R8 fieldwise IBLT test](nachtlorn-fieldwise-and-poem-keys.md) used
selected alphabets and admitted letter transforms. This continuation closes a
specific schema question: can **any** bijective alphabet make the **raw** body fit those
fixed-width fields? It uses finite arithmetic certificates, not a solver or
another password grid. Registration preceded the source computation.


The [earlier packed-object analysis](nachtlorn-construction-checks.md) already
used the leading-capacity principle on homogeneous 7/14-letter blocks. R18 is a
schema-specific application with independent source-index certificates, not a
new mathematical principle or the first alphabet-independent capacity test.

## Registered construction and results

The schema is unchanged from R8:

| Field | Letters | Unsigned bit-pattern width | A0 leading-glyph capacity | A1 leading-glyph capacity |
|---|---:|---:|---:|---:|
| Count | 7 | 32 | 14 | 13 |
| Key | 14 | 64 | 8 | 7 |
| Checksum | 7 | 32 | 14 | 13 |

A0 assigns glyph digits 0–25; A1 adds one to each digit in the base-26
polynomial. Both cell-interleaved and field-major layouts are admitted, with
most-significant letter first or last **within each field**. This is digit order,
not the endianness of a byte serialization. No header, offset, letter cipher,
padding insertion, truncation or modulo reduction is admitted.

The full 8,736 letters divide into 312 cells of 28 letters. In **each** layout
and digit direction, **all 26 glyphs occur in the most-significant position of
each field type**. There are not enough permitted leading digits for any
bijection to make all fields fit.

| Source variant | Cases: layouts × directions × biases | Result |
|---|---:|---|
| Full body | 8 | Exact leading-capacity exclusions; all three field types independently fail |
| Remove only final I | 8 | Dimension failure: 8,735 leaves remainder 27 modulo 28 |

The report contains **24 independently replayable field certificates** for the
eight full-body cases. Even giving each field type its own fixed alphabet cannot
repair these failures. A varying alphabet per cell is outside the model.

- [Machine-readable results and certificates](data/nachtlorn-reset-field-capacity-results.json)
- [Registered scope and outcome](data/nachtlorn-reset-plan.json)
- [Probe and independent verifier](../scripts/nachtlorn_field_capacity.py)
- [Regression tests](../tests/test_nachtlorn_field_capacity.py)

## Why alphabet enumeration is unnecessary

For a width-`w` field, let each glyph's assigned digit `d` be in 0–25 and let
bias `a` be 0 or 1. Its value is

```text
N = sum((d[glyph_j] + a) * 26**(w-1-j))
G = (26**w - 1) // 25
```

All zero-based digit contributions are nonnegative. Therefore the leading glyph
must satisfy

```text
d[leading] * 26**(w-1) + a*G <= 2**bits - 1
```

Counting the possible leading digits gives the capacities in the table above.
This relaxes the suffix digits to independent zeros: repeated glyphs and
bijection requirements can only tighten the bound. More distinct leading glyphs
than permitted digits is a pigeonhole contradiction. No assumptions about hashes,
count magnitudes, checksums, peeling or literary names are needed.

### A nine-letter certificate

For full-body, cell-interleaved, most-significant-first A0 **key** fields, the
first nine leading glyphs are already distinct:

```text
body-letter index:   7  35  63  91 119 147 175 203 231
glyph:               I   E   X   N   M   R   W   K   S
```

Indices are zero-based in the original body with whitespace removed. Nine
distinct glyphs require at least one assigned digit to be 8 or greater. Its
14-letter field is then at least

```text
8 * 26**13 = 19,849,222,985,629,892,608
2**64 - 1 = 18,446,744,073,709,551,615
```

so it cannot fit 64 bits. Relabelling letters cannot change this contradiction.
Other layouts and digit orders have their own saved source-position witnesses.

## Validation and reproducibility

The certificate verifier does not call the capacity calculator or scanner. It
recomputes the allowed leading digits with direct integer arithmetic, checks
the witness positions against the selected layout/field/direction, checks the
source glyphs and their distinctness, and verifies that there is one more witness
than available digits.

Eleven new tests cover direct inequality boundaries, exhaustive small-alphabet
permutations, synthetic in-range fields under both biases/layouts/directions,
certificate tampering, independent replay, unchanged schema, dimension failures,
invalid parameters and source-overwrite protection. Passing width controls are
not described as valid IBLTs. The saved source certificates also replay in tests.

**261 tests across 30 research modules pass**, with the previously used optional
Z3, cvc5 and cryptography dependencies available (19.323 seconds). R18 itself
uses only Python's standard library; it issues no solver queries. Full-repository
Ruff also passes. These are local checks, not a new GitHub CI run.

```bash
python3 scripts/nachtlorn_field_capacity.py docs/data/nachtlorn-transcript.txt \
  --output scratch/nachtlorn-r18-replay.json
python3 -m unittest tests.test_nachtlorn_field_capacity -v
```

Original source remains 11,129 bytes, SHA256
`04eddf97e8ebbc9ce2565269508d63c99b60efc7cacf3f2c020f14215dc67e7e`.
No source letters or whitespace were modified.

## What this does not settle

This excludes only the registered raw, fixed-width, headerless field encoding.
It does **not** disprove IBLTs, Bloom-related constructions, a distinct serialization,
an intervening transformation, another schema or a book reference. The field
encoding was a research hypothesis, not a serializer supplied by the author or
the pinned reference implementation. Negative counts do not rescue overflow:
a signed32 two's-complement count still needs a 32-bit bit pattern.

The [R16/R17 gzip cases](nachtlorn-stored-gzip.md) remain UNKNOWN; no old timeout
has been rerun or relabelled. The final I is not established as padding or as an
outlier. Another IBLT test needs independent grounds for its actual encoding,
not merely a dimension fit. Recovery must still identify a real construction,
then a recovered population and an independently justified outlier rule.
