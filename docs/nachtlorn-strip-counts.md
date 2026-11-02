# Reproducing the proposed vertical-strip counts

**This reproduces the earlier visual hypothesis; it is not a new cipher result.**
The user proposed rotating the pages sideways and treating **one original row as
one vertical strip**. A further proposal places zero at the final printed I; that
choice is not confirmed as the author's intended guide. The user subsequently
chose to keep I as a provisional zero while investigating a range-comparison
rule.

To make the earlier externally stored per-row counts reproducible in this
repository, the [counting script](../scripts/nachtlorn_strip_counts.py) reads the
unchanged transcript. In this fixed model, zero is at the terminal I's original
zero-based column **48**. With counterclockwise rotation, letters at smaller
original columns are below zero and those at larger columns are above. A letter
exactly on zero is counted separately. Spaces preserve physical columns but are
not counted as letters. Clockwise rotation exchanges above and below; it does not
alter the row identities or letter counts.

## Inspect the complete strips

[Open the reconstructed I-zero strip diagram](data/nachtlorn-strip-view.svg).
It displays each original row as a vertical column, with body rows 1–61 and
62–146 marked as the two supplied pages. Every letter occupies its original
character-column position; indentation and group spaces remain gaps. The red
horizontal line is the **provisional** I-zero guide. Zoom in to read the
letters; hover over a strip for its original row text in an SVG-capable viewer.

This is a transcript-derived diagram with upright glyphs, **not** a rotated page
photograph: the original header, margins, page rules and font geometry are not
reproduced. Rows are arranged left to right in original order; increasing
original character columns run upward. It neither identifies a letter operation
nor supplies a new solution. Its [generator](../scripts/nachtlorn_strip_view.py)
is separately tested against every original glyph's row, physical column and
rendered coordinate.

## Reproduced result

For the 145 complete rows, grouped here solely for display by their existing
indentation, the result exactly reproduces the archived table:

| Indent | Below | On zero | Above | Rows |
|---:|---:|---:|---:|---:|
| 0 | 40 | 1 | 19 | 19 |
| 1 | 40 | 0 | 20 | 20 |
| 2 | 39 | 1 | 20 | 17 |
| 3 | 38 | 1 | 21 | 18 |
| 4 | 37 | 1 | 22 | 16 |
| 5 | 36 | 1 | 23 | 16 |
| 6 | 35 | 1 | 24 | 22 |
| 7 | 35 | 0 | 25 | 17 |

The final row has **35 below, the I on zero, and 0 above**, or the proposed
signed count range **[−35, 0]**. This is the same known short final row, not a
second independent anomaly: its I is on zero by construction. The 145 complete
rows have eight repeated patterns, each occurring 16–22 times. Differences in
ranges alone do not identify a unique full-length row or final answer.

Two simple, explicit **descriptive** comparison rules agree on row 146: it is the
only row whose exact signed count pair occurs once, and the only row with the
minimum above-zero count (0; every other row has 19–25). If row 146 is removed,
no exact count pair is unique and the minimum above-zero count, 19, is shared by
19 rows. These rules describe the same short-row fact and are not independent
evidence for an answer or a demonstrated authorial selection rule. They do not
replace the user's proposed final-layer outlier with the last printed row.

[All 146 per-row counts](data/nachtlorn-strip-counts.json) are retained as
individual records rather than pooling positions across the page. Each row's
below + on + above equals its literal number of letters. The script reports exact-range frequencies and above-zero extrema, without
choosing a statistical fence, searching guide positions, decoding letters, or
assigning an answer. The historical 1.5×IQR calculations and their qualifications remain in
the [archive](nachtlorn-analysis.md#counted-characters-versus-coordinate-distances);
this reproduction independently verifies the count table, not those fence
calculations.

## What remains unresolved

The physical-strip grouping and letter-count interpretation follow the user's
clarification. The final I as zero remains a **proposed** guide. Neither the
source poem nor the layout-only RNG reconstruction independently establishes
that guide or a rule for carrying the short row into the final recovered-object
layer. The user also described the answer as an outlier on the *last layer*, not
necessarily the last printed row. Treating row 146 as the answer would conflate
those distinct ideas.

The source remains 11,129 bytes with SHA256
`04eddf97e8ebbc9ce2565269508d63c99b60efc7cacf3f2c020f14215dc67e7e`.
No page, space, letter or line was modified. This is a reproducibility follow-up,
not another pre-registered answer search or independent corroborating discovery.

## Validation

Eight tests cover hand-counted strips, a guide falling on a space, indentation,
trailing spaces, invalid input, tied extrema and unique-range handling, source-overwrite protection, and independent
slice-based replay of all 146 actual rows against the historical eight-pattern
table. **289 research tests across 33 modules passed** locally, including the
previous optional dependencies; full-repository Ruff passed. The count script
itself uses only the Python standard library.

```bash
python3 scripts/nachtlorn_strip_counts.py docs/data/nachtlorn-transcript.txt \
  --output scratch/nachtlorn-strip-counts-replay.json
python3 -m unittest tests.test_nachtlorn_strip_counts -v
```
