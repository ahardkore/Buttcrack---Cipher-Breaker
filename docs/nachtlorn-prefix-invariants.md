# Nachtlorn — an exact representation exclusion, not another guessed key

**Status: unresolved. No plaintext, recovered population, or final outlier.**

R14 executes the representation-first gate left after the
[replacement-role assessment](nachtlorn-replacement-roles.md). It tests an entire
class of digit alphabets, rather than selecting more words from the poem or book.
The [registered model](data/nachtlorn-reset-plan.json) was recorded before this
body test. This is exploratory model testing, not a held-out prediction or an
author-confirmed account of the construction.

## Result

Under the precise model below, **gzip, bzip2 and XZ are impossible for every
permutation of the 26-letter digit alphabet**. This covers all
**403,291,461,126,605,635,584,000,000 = 26!** digit alphabets in each model,
not just BLOOM, BLACK, GREEN, WHITE or the conventional A–Z order.

| Original-letter input | Digit convention | gzip-compatible alphabets | bzip2-compatible alphabets | XZ-compatible alphabets | zlib-header-compatible alphabets |
|---|---|---:|---:|---:|---:|
| Full 8,736 letters | 0–25 | 0 | 0 | 0 | 810,167,137,515,394,154,496,000 |
| Full 8,736 letters | 1–26, bijective | 0 | 0 | 0 | 806,029,552,289,077,788,672,000 |
| Explicit final-I removal | 0–25 | 0 | 0 | 0 | 74,439,502,744,180,654,080,000 |
| Explicit final-I removal | 1–26, bijective | 0 | 0 | 0 | 43,582,481,579,832,459,264,000 |

The A0 counts conservatively permit a zero-valued first glyph in a fixed-width
numeral. The result JSON also counts canonical A0 numerals without that leading
zero. All three exclusions hold for the larger, more permissive class and thus
also for the canonical subset.

The zlib column is **not a recovery**. A two-byte zlib header is compatible with
many unrelated alphabets. The report includes arbitrary deterministic completions
that certify header compatibility only. They are not recovered keys; their data
has not been accepted as a complete, checksum-valid zlib stream. No packet or
answer is selected by English scoring or by an attractive header.

Changing the terminal-I convention changes numeral length and byte alignment.
The different counts do **not** establish that I is padding, zero, or an outlier.

## Exactly what was tested

1. Preserve the original letter order; optionally remove only the final I as a
   separately labelled hypothesis.
2. Assign each distinct glyph a distinct digit, using all digits 0–25 or 1–26.
3. Interpret the entire numeral as one integer, most-significant digit first.
4. Write the integer as **minimal big-endian bytes**.
5. Require a format header at byte offset zero:
   - **gzip:** `1f8b08` and every one of the 32 legal flag bytes. Timestamp,
     optional fields and remaining payload are not guessed.
   - **zlib:** all 66 two-byte headers with compression method 8, window indicator
     0–7 and a valid FCHECK. Dictionary and compression-level flags remain free.
   - **bzip2:** `BZh1` through `BZh9`, followed by either the first-block marker
     `314159265359` or the empty-stream/end marker `177245385090`.
   - **XZ:** only the six-byte stream magic `fd377a585a00`; no flags or CRC are
     imposed, so rejection does not depend on a particular check algorithm.

The exact extrema over digit permutations determine feasible byte lengths:
5,132–5,133 bytes, except full-body A1, which requires 5,133 bytes. Across the
four models there are **819 header/byte-length intervals**, all tested without
a search cutoff. There is no leading-zero-byte restoration for these offset-zero
headers: all start with a nonzero byte, and prepending zeros would invalidate
the claimed header position.

This test does **not** cover little-endian bytes, reversed numeral digits,
blockwise encodings, an intervening letter cipher, book operations, arbitrary
embedded offsets, or formats without these headers. In particular, it does not
exclude every compressed or binary construction.

## Why 26! alphabets do not need enumeration

For a header of `m` bytes in a minimal `n`-byte integer, the header specifies an
inclusive integer interval:

```text
low  = header_integer * 256**(n-m)
high = (header_integer + 1) * 256**(n-m) - 1
```

For the bijective convention, subtract the fixed geometric-sum bias to express
the same interval using digits 0–25. A base-26 digit prefix also specifies an
integer interval. Traverse only intersecting prefixes:

- repeated glyphs must reuse their previously assigned digit;
- different glyphs cannot reuse the same digit;
- a disjoint interval contributes zero;
- a prefix interval wholly inside the header interval contributes the factorial
  of the number of unassigned digits, exactly.

Only boundary prefixes need further traversal. The implementation uses an
iterative stack, exact integers and no permutation cap, timeout, or heuristic
English threshold. Counts include permutations of unused glyphs when a synthetic
control uses fewer than 26 symbols; they count complete alphabets, not distinct
integer values.

### An independently checkable short contradiction

The source begins `VXGFAG`. The same G appears in positions 3 and 6; V, X, G,
F and A must have distinct digit values under a bijection.

For example, a full-body A0 numeral encoding a 5,133-byte gzip stream beginning
`1f8b0800` would force its first six digits to be:

```text
source glyphs: V  X   G   F   A   G
forced digits: 6  5  22  20  21  13
```

G cannot be both 22 and 13. This example alone rejects only that header and byte
length. The independent regression test goes further: it exhausts every possible
six-digit prefix implied by **every admitted gzip, bzip2 and XZ header interval**
in all four models. Every prefix violates equality, injectivity, or the numeral's
range. Thus the three exclusions can be checked without trusting the symbolic
factorial-counting implementation. No body characters after `VXGFAG` are needed
for this final contradiction once the input width is fixed.

## Controls and reproducibility

Eleven tests pass, including:

- exact count and bound comparisons against exhaustive four-symbol permutations;
- inclusive interval endpoints, fixed mappings and unused-glyph completions;
- fixed-width leading zeros versus the bijective convention;
- known relabelled gzip, zlib, bzip2 and XZ synthetic members under both biases;
- real empty bzip2 and preset-dictionary zlib header coverage;
- the independent six-glyph exclusion certificate;
- exact replay of the published result and original-source SHA256;
- refusal to overwrite the source.

```bash
python3 -m unittest tests.test_nachtlorn_prefix_invariants -v
python3 scripts/nachtlorn_prefix_invariants.py docs/data/nachtlorn-transcript.txt \
  --output docs/data/nachtlorn-reset-prefix-invariant-results.json
```

The new probe and its eleven tests require only the Python standard library.
The broader focused research regression passes **217 tests across 26 modules**
(with the existing optional PyCryptodome research dependency), in 25.269 seconds.
Ruff passes; working-tree integrity checks cover **482 Python sources and 71
Markdown files**, including the new files, with no syntax or
local-link defects. The full application-wide suite was not rerun in this pass.

The original transcript remains
11,129 bytes with SHA256
`04eddf97e8ebbc9ce2565269508d63c99b60efc7cacf3f2c020f14215dc67e7e`.

[Exact machine-readable results](data/nachtlorn-reset-prefix-invariant-results.json)
record every header family, all feasible byte lengths, exact counts, search-node
counts and clearly labelled header-only witnesses.

## Decision and next gate

Do not spend more keyword guesses on **raw, whole-integer, big-endian** gzip,
bzip2 or XZ: arbitrary alphabet relabelling cannot rescue them. That is a scoped
mathematical exclusion, not evidence that the cipher is impossible.

Do not promote zlib merely because its short header survives. A valid complete
stream, or an independently justified construction invariant, is still required
before claiming a packet or choosing an alphabet. The complementary
[little-endian congruence check](nachtlorn-little-endian-invariants.md), executed
later as R15, finds gzip/zlib/XZ header-compatible alphabets but no complete packet
among its arbitrary witnesses; bzip2 feasibility times out. That result does not
change this big-endian exclusion. No new encryption stage or literary population
is inferred from the three exclusions.
