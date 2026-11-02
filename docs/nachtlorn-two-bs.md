# A literal “neither be right” strip check

**R22: this speculative raw-letter rule does not select one full strip.** No
plaintext, recovered population or final outlier is claimed.

The user chose to retain the final I as a **provisional zero** for the sideways
strip idea. [R21](nachtlorn-strip-geometry.md) showed that comparing only the
numbers of letters on either side cannot distinguish the letters themselves.
This continuation tests one narrowly specified, content-aware possibility.

## Hypothesis and fixed rule

As an exploratory pun, read “neither be right” as **two literal B glyphs,
neither to the right** of the I-zero guide. This is not a confirmed instruction:
“be” need not mean B, “neither” need not count glyphs, and the line could apply
only after some still-unknown recovery layer. The author has not specified this
predicate. It was registered before checking its source results.

On each of the **145 full original rows**, using the original physical column of
the final I (zero-based 48), require:

- exactly two literal `B` glyphs in that row;
- both strictly to the **left in the original orientation** (below the guide
  on a counterclockwise-rotated page);
- no B exactly on the guide or to its right.

Every original row is evaluated separately. Spaces preserve physical columns but
are not letter slots. The short final row is reported separately as a boundary
control, not assumed to be the final answer. No other glyph, guide, orientation,
letter count, decryption or selection rule was searched in R22.

## Result

- **39** full rows contain exactly two Bs anywhere.
- **21** of those rows have both Bs strictly left of the guide; the other 18 do
  not satisfy the whole predicate.
- The last, short row has **one** B on the left and no Bs on or right of the
  guide, so it does not satisfy the two-B predicate.

Thus the rule fails the registered necessary condition for a **unique full-row
selection**. It supplies no reason to privilege any one of the 21 matches. This
is a negative only for this direct raw-row reading; it does not exclude a
transformed or object-level application of the poem.

For a limited sanity check, condition on each full row's actual B count and
physical letter slots, and imagine uniformly relocating that row's B glyphs
among those slots. A row with exactly two Bs has probability
`choose(left_slots, 2) / choose(60, 2)` of matching; any row with a different B
count has probability zero. Summing these rowwise probabilities gives an expected
**15.1531 matches** under that conditional model. The observed 21 is reported
alongside it, not presented as a p-value, a global significance calculation or a
model of the author's cipher. This expectation cannot validate or invalidate a
clue interpretation.

## Reproducibility and limits

- [Fixed registration and outcome](data/nachtlorn-reset-plan.json)
- [All individual counts, matching rows and exact expectation](data/nachtlorn-two-bs-results.json)
- [Probe](../scripts/nachtlorn_two_bs.py) and [tests](../tests/test_nachtlorn_two_bs.py)

Six tests cover rule boundaries, guide-on-B rejection, letter slots versus
spaces, exhaustive small synthetic permutation probabilities, wrong B counts,
input/overwrite protection, and independent slice-based source replay. All
**300 tests across 35 research modules passed** locally, with prior optional
research dependencies present; full-repository Ruff passed. This probe itself
uses only the standard library.

The transcript remains 11,129 bytes, SHA256
`04eddf97e8ebbc9ce2565269508d63c99b60efc7cacf3f2c020f14215dc67e7e`.
No original letter, spacing or line was changed. The result does not assign the
last printed row as the last-layer outlier. It leaves open the user's visual
hypothesis, other interpretations of “neither be right,” and the missing bridge
from construction to recovered objects and their outlier rule.

```bash
python3 scripts/nachtlorn_two_bs.py docs/data/nachtlorn-transcript.txt \
  --output scratch/nachtlorn-two-bs-replay.json
python3 -m unittest tests.test_nachtlorn_two_bs -v
```
