# How unusual is the largest letter count?

**R28 is a retrospective baseline calculation, not an identified outlier or a
cipher solution.** The historical analysis already recorded that `E` occurs
412 times and is unusually high under a fixed-glyph uniform model. After that
observation—and after the R27 page counts were inspected—this follow-up
quantifies the selection of the largest of 26 glyph counts.

The unmodified body contains **8,736** letters. Its largest count is **412**,
for E; the ideal independent, uniform-letter expectation for each glyph is
8,736 / 26 = **336**. Under that ideal null, one specified glyph has a
`Binomial(8736, 1/26)` count. Exact integer arithmetic gives

```text
Pr(specified glyph count >= 412) = 0.0000234678679038...
Pr(any of 26 glyph counts >= 412) <= 0.000610164565500...
```

The second line is the **union bound**, not an exact probability for the
maximum. It corrects for choosing whichever of the 26 glyphs had the largest
count. It does **not** correct for the many earlier tests or the post-observation
choice to examine this statistic. The result is evidence against the particular
ideal iid-uniform model, not proof about how the text was generated.

The same glyph has 181 occurrences on page 1 and 231 on page 2. Those are
**descriptive** counts: E was already identified from the full body, so the
page split is not a clean independent discovery of E. The preceding
[held-out mixture test](nachtlorn-heldout-mixture.md) did not find a predictive
English/uniform mixture across pages.

## What this does—and does not—tell us

A perfect uniformly random independent-letter model is not a safe assumption
for the body. But the result does not identify a key or decoder, establish
whether the excess is intentional, or distinguish biased sampling, dependence,
a particular PRNG, hidden content, or other constructions. The cipher may have
an atypical outcome under a model without that model being impossible.

**E is not asserted to be the answer.** This global histogram is a separate
cryptanalytic diagnostic, not the user's visual model of one original row per
vertical strip with counts on either side of a provisional I-zero guide. It does
not resolve the missing recovered-object population or the final-layer outlier.

## Reproduce and verify

- [Registration, explicitly post-observation](data/nachtlorn-reset-plan.json)
- [Counts and bound](data/nachtlorn-maximum-count-null.json)
- [Exact integer calculation](../scripts/nachtlorn_maximum_count.py) and
  [tests](../tests/test_nachtlorn_maximum_count.py)

The binomial tail is summed as exact integer terms divided by `26**8736`; the
printed decimal is a 30-digit Decimal rendering. Four tests compare it with
independent direct binomial sums, exhaustively verify the union bound for small
alphabets, exercise boundary and overwrite guards, and independently replay the
source histogram and a floating log-sum. **337 tests across 42 research modules
passed** locally with earlier optional dependencies; whole-repository Ruff passed.
The new diagnostic itself uses only the standard library.

The transcript remains unchanged, SHA256
`04eddf97e8ebbc9ce2565269508d63c99b60efc7cacf3f2c020f14215dc67e7e`.

```bash
python3 scripts/nachtlorn_maximum_count.py docs/data/nachtlorn-transcript.txt \
  --output scratch/nachtlorn-maximum-count-replay.json
python3 -m unittest tests.test_nachtlorn_maximum_count -v
```
