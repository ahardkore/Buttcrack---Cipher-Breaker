# Nachtlorn — the formatting seed does not supply a shared RNG recipe

**R19: scoped construction failures; no body decryption or final outlier.**

The strongest reproduced construction component remains the layout: consecutive
native `random.Random(4300).randrange(8)` draws match every leading-space count.
This experiment asks a different question: would the same seeded RNG instance
still produce those spaces if it also generated the body letters using common
native calls?

The answer is **no for all 15 registered recipes**. This is not a general proof
against shared RNGs, a unique-seed result, or evidence that all body generators
have been eliminated. Registration preceded the actual-source computations.

## Fixed models, not another seed or key search

There are five letter-draw methods and three schedules, seeded once at 4300:

| Method | Batch for each original row |
|---|---|
| `randrange26` | One native `randrange(26)` per letter, including rejection draws |
| `choices26` | Native `choices(range(26), k=row_length)` |
| `bits5_mod26` | One native `getrandbits(5) % 26` per letter |
| `bits8_mod26` | One native `getrandbits(8) % 26` per letter |
| `row_randbytes_mod26` | Native `randbytes(row_length)`, each byte reduced modulo 26 |

Schedules:

1. Draw a row's indent, then its letters, repeatedly.
2. Draw a row's letters, then its indent, repeatedly.
3. Draw every row's letters first, then all indents, without reseeding.

The original row sizes are retained: 145 rows of 60 letters and one of 36. There
is no unknown offset, seed search, extra call, reseed, saved/restored state or
comparison to actual letter values. A letter relabelling or post-generation
literal overwrite cannot repair a mismatched indent without changing the recipe.
An insertion scheme that changes which RNG calls occur is outside this model.

## Exact result

| Schedule | Parameter recipes | Earliest mismatch in every recipe |
|---|---:|---|
| Indent then row | 5 | Body row 2 |
| Row then indent | 5 | Body row 1 |
| All rows then indents | 5 | Body row 1 |
| Known indentation-only baseline | 1 | None: 146/146 match |

For the first schedule, body row 1 correctly has seven leading spaces. After
that first row's letter draws, the predicted second indent is already wrong:

| Letter method | Predicted row-2 indent | Observed | MT words consumed before that indent |
|---|---:|---:|---:|
| `randrange26` | 7 | 0 | 81 |
| `choices26` | 3 | 0 | 122 |
| `bits5_mod26` / `bits8_mod26` | 6 | 0 | 62 |
| `row_randbytes_mod26` | 5 | 0 | 17 |

Native rejection matters: `randrange(8)` requests **four** bits and rejects values
8–15, rather than consuming one three-bit draw per indent. The known 146-indent
baseline consumes **323 MT words**. The traced subclass delegates each call to
native `Random`; it does not replace the random-number algorithm.

There are **12 distinct full indentation predictions**, not 15 independent
predictions. Five-bit and eight-bit draws consume one MT word per letter, so
they are clock aliases within each schedule, despite producing different letter
values. The report groups these aliases explicitly. Some rows happen to match
in failed recipes; no partial-match score is treated as recovery or a p-value.

- [Machine-readable predictions and mismatch records](data/nachtlorn-reset-layout-clock-results.json)
- [Registration, exclusions and outcome](data/nachtlorn-reset-plan.json)
- [Native clock probe](../scripts/nachtlorn_layout_clock.py)
- [Independent replay and regression tests](../tests/test_nachtlorn_layout_clock.py)

## Historical overlap and validation

Earlier archived MT work tested eight fixed one/two-word interleavings for letter
and indentation generation. R19 is a finite native-API follow-up, including
variable rejection and row-batched bytes, not a claim that shared-RNG schedules
had never been considered. The indentation-only match and 323-word consumption
are previously known facts, reproduced here as controls.

Twelve new tests compare generated values and final states to plain native
`Random`, manually replay rejection loops, check bit/float/byte word consumption,
exercise ragged batch boundaries, recover synthetic schedule compatibility while
retaining aliases, verify mismatch positions, preserve global RNG state, guard
source overwrites, and independently replay all published source predictions.

**273 tests across 31 research modules pass** (19.225 seconds) with the prior
optional research dependencies present. R19 itself is standard-library-only;
no solver or actual-source letter decoding is invoked. Full-repository Ruff
passes. These are local checks, not a new GitHub CI run. The recorded source run
uses Python **3.11.2**, and its runtime version is retained in the JSON.

```bash
python3 scripts/nachtlorn_layout_clock.py docs/data/nachtlorn-transcript.txt \
  --output scratch/nachtlorn-r19-replay.json
python3 -m unittest tests.test_nachtlorn_layout_clock -v
```

Source remains 11,129 bytes, SHA256
`04eddf97e8ebbc9ce2565269508d63c99b60efc7cacf3f2c020f14215dc67e7e`.
No wording, body glyphs, spaces or line breaks were changed.

## Consequence for the investigation

The verified layout fit does **not** justify silently carrying the same seed and
RNG state into a body-generation model. The tested direct schedules fail before
any message interpretation is needed. Separate instances, a reseed before
formatting, letters generated without that RNG, different calls, or more complex
schedules remain possible. This experiment does not distinguish among them.

No new seed offset, cipher layer or literary population is selected from these
failures. [R18's field-encoding exclusions](nachtlorn-field-capacity.md) remain
scoped, and [R16/R17's gzip timeouts](nachtlorn-stored-gzip.md) remain UNKNOWN.
The construction → recovered population → independently justified outlier bridge
is still missing. The original-row visual hypothesis remains open, requiring an
independently grounded anchor rather than a guide chosen to fit a candidate.
