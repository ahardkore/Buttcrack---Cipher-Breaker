# What the I-zero strip ranges can and cannot reveal

**R21: all 146 ranges follow exactly from the existing line geometry.** This is
not a new plaintext, final answer, or disproof of the user's visual idea.

The user chose to keep the final I as a **provisional zero** and investigate
comparisons of individual sideways strips. The previous [count reproduction](nachtlorn-strip-counts.md)
found that the last row alone has range **[−35, 0]**, while full rows repeat
eight patterns. The question here is whether those counts contain information
about which letters appear in a row, beyond the fact that they are letters.

## Registered check

For a row with d leading spaces, n letters in five-letter groups, and one space
between groups, zero-based letter number j has original physical column

```text
column(j) = d + j + floor(j / 5),    0 <= j < n.
```

Fix zero at the last I's actual column, 48. Count positions below, on, and above
that column. This prediction uses row length, indentation and grouping only—not
glyph identities or a chosen output. The check compares **every predicted
position**, not only each resulting range, against each unchanged original row.

Result: **146/146 rows match at every letter position**, and **146/146 predicted
below/on/above counts match the direct counts**. The first 145 rows have 60
letters apiece; the last has 36. The script and data record each row separately.
The predicted and actual position counts are checked against the earlier
independent slice-based result.

The final row has indent 6: its last letter is j=35, hence
`6 + 35 + floor(35 / 5) = 48`. It therefore ends exactly at the selected guide,
with 35 letters below and its I on zero. This is a consequence of the row length,
grouping and choice of guide. The I's location is a valid *hypothesis* for a
reference; this calculation cannot establish that the reference was intended.

## Counterfactual and implication

As a control, the tests change every body letter except the final I to the next
alphabetical letter **in memory**, preserving all spaces, line boundaries and the
final guide. The entire per-row range report is identical. The altered body is
not proposed as a solution, and the source is never rewritten.

Consequently, any rule based **only** on these per-row range counts must produce
the same result for both bodies. In particular, the unique short-row range is
not evidence about the actual letter values, nor is it an independently recovered
object or final-layer outlier. The full rows with the same indent necessarily tie
under this model; their actual letters cannot break that tie in a count-only rule.

This does **not** rule out a role for preserved spacing, a content-dependent
visual extraction, another justified guide, or an outlier among objects recovered
later. It also does not prove the separate formatting RNG was used by the author:
the [layout reconstruction](nachtlorn-reset.md) is a compatible model, not unique
provenance. A viable next step needs a reason to incorporate letter identity or
recover objects, not another selected count threshold.

## Reproducibility and checks

- [Registered design and result](data/nachtlorn-reset-plan.json)
- [Per-row predicted and actual counts](data/nachtlorn-strip-geometry.json)
- [Geometry checker](../scripts/nachtlorn_strip_geometry.py) and
  [controls](../tests/test_nachtlorn_strip_geometry.py)

Five tests cover grouped synthetic rows of different sizes and indentations,
extra gaps that break position matching even when counts happen to agree,
letter-replacement invariance, invalid inputs and overwrite protection, and all
actual rows against the independently calculated count record. **294 tests across
34 research modules passed** locally with prior optional dependencies installed;
whole-repository Ruff passed. The new checker uses only the standard library.

The original transcript remains 11,129 bytes, SHA256
`04eddf97e8ebbc9ce2565269508d63c99b60efc7cacf3f2c020f14215dc67e7e`.
No source text or layout was changed.

```bash
python3 scripts/nachtlorn_strip_geometry.py docs/data/nachtlorn-transcript.txt \
  --output scratch/nachtlorn-strip-geometry-replay.json
python3 -m unittest tests.test_nachtlorn_strip_geometry -v
```
