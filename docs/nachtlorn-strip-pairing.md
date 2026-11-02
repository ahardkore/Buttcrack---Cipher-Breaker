# A content-sensitive test around the provisional I-zero guide

**R23: one specific mirror-pair construction fails, even allowing one exceptional
full row.** No ciphertext has been decoded and no final outlier identified.

The user's model counts letters on either side of zero in each vertical strip;
the user chose the final I as a **provisional** zero. This experiment adds a
separate exploratory assumption: pair letters outward from that guide and ask
whether one shared substitution relates the two sides. That pairing and
substitution are **not** instructions supplied by the user or author, nor a
necessary part of the count-only interpretation.

## Fixed construction

For each of the 145 full original rows, use physical column 48 as zero, omit any
letter exactly on the guide, and count printed letters rather than spaces. Pair
nearest-to-zero letters on either side, then the next-nearest, and so on until
one side runs out. Extra letters on the longer side are left unpaired. The
short final row is retained in the source but excluded from this test: it has
no letters on the far side and thus no pairs.

The hypothesized structure is one **fixed, unknown bijective substitution**
mapping every paired left glyph to its right glyph across all but at most one
full row. Identity is included as a special case. This is a construction
hypothesis, not an assumption that the visible text must be plaintext. Its
parameters and falsification rule were registered before the source run.

## Exact contradiction

The 145 rows give **3,152 pairs**. No common bijection satisfies the pairs;
independently trying the omission of each single full row also leaves no
compatible mapping. A small certificate explains why. Columns are zero-based
original transcript character columns, and pair numbers count outward from the
provisional guide:

| Body row | Pair | Left column and glyph | Right column and glyph | Required mapping |
|---:|---:|---|---|---|
| 1 | 1 | 47: K | 49: E | K → E |
| 1 | 3 | 45: K | 51: H | K → H |
| 2 | 1 | 46: T | 49: P | T → P |
| 2 | 3 | 44: T | 51: W | T → W |

Row 1 requires K to map to both E and H; row 2 requires T to map to both P and
W. Each contradiction is internal to its own row, so they survive **even if
separate fixed substitutions per row are allowed**. Omitting at most one row
cannot remove both contradictions. Spaces and glyphs on zero are not paired;
all four observations can be replayed from the unchanged transcript.

This is not a claim that a mirror rule is author-intended or that two independent
outliers exist. It only falsifies this exact model with its declared tolerance.
Other pairings, per-position mappings, transformations before pairing, a
context-dependent or stateful operation, additional noise or an outlier among
recovered objects are outside the test. The displayed same-input conflicts also
exclude a single fixed function per affected row, even if it is non-bijective. The original range-count hypothesis is not rejected.

## Validation and provenance

- [Registration and outcome](data/nachtlorn-reset-plan.json)
- [Complete per-row pair counts and certificate](data/nachtlorn-strip-pairing-results.json)
- [Probe](../scripts/nachtlorn_strip_pairing.py) and [tests](../tests/test_nachtlorn_strip_pairing.py)
- [Transcript-derived strip diagram](data/nachtlorn-strip-view.svg)

Six tests cover synthetic bijective and one-exception positives, independent
small exhaustive conflict-graph enumeration, same-row disjoint conflicts,
certificate tampering, ignored spaces/on-guide letters, source overwrite guards,
and independently replaying the source certificate plus every single-row
omission. **309 tests across 37 research modules passed** locally with prior
optional research dependencies; full-repository Ruff passed. The new probe is
standard-library-only. No word scoring, seed search, or solver is used.

The transcript remains 11,129 bytes, SHA256
`04eddf97e8ebbc9ce2565269508d63c99b60efc7cacf3f2c020f14215dc67e7e`.
All original letters, spaces, and line breaks remain unchanged.

```bash
python3 scripts/nachtlorn_strip_pairing.py docs/data/nachtlorn-transcript.txt \
  --output scratch/nachtlorn-strip-pairing-replay.json
python3 -m unittest tests.test_nachtlorn_strip_pairing -v
```
