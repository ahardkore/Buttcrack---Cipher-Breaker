# Nachtlorn — whole-block and packed-object construction checks

**Status: unresolved. No new plaintext or final outlier recovered.**

Subsequent work: [binary envelopes and byte-layer recovery](nachtlorn-binary-recovery.md).

These experiments follow the author's reported distinction between construction,
recovery and interpretation. They test objects that need not look like English
at an intermediate stage. **No English-scoring gate or preferred answer word was
used to accept or reject the actual data.** The final singleton I was retained.

## 1. Could the filler have been generated as whole base-26 blocks?

Earlier generator searches mostly treated letters as individual draws. A different
construction draws an integer for a whole block, then expands its base-26 digits.
That changes both the output and MT word-consumption schedule.

The new test covered:

- Seeds: integer **4300**, and the five strings **BLOOM**, **BLPNM**, **NACHTLORN**,
  **Nachtlorn**, **nachtlorn**, using native Python string seeding, version 2.
- Sixteen block widths: **2, 3, 4, 5, 6, 7, 10, 12, 14, 20, 26, 30, 60, 3660,
  5076, 8736**. These include printed-group/row sizes, the previously identified
  page letter counts, the complete body, and the 7/14-digit hypothesis below.
- Integer draws: native `randrange(26**width)`, `getrandbits` reduced modulo that
  bound, literal `int(random()*bound)`, and exact rational 53-bit scaling.
  Native floating multiplication was omitted for the three enormous bounds
  that overflow it. Rational scaling is explicitly a different model.
- Both digit orders; every initial raw MT-word offset **0–1024**, inclusive.
- **Five independent unknown substitution alphabets**, allowing a fixed
  five-letter Vigenere layer without guessing its key.

Each candidate first had to explain the **unaltered first 120 letters** exactly
under bijections. A surviving candidate would learn its mappings from the first
**3,000 letters**, then predict the remaining **5,736** without fitting them.

| Actual-data run | Configurations | Prefix matches | Training fits |
|---|---:|---:|---:|
| Known layout seed, original fourteen widths | 108,650 | 0 | 0 |
| Five poem/title string seeds, original widths | 543,250 | 0 | 0 |
| Supplementary widths 7 and 14, all six seeds | 98,400 | 0 | 0 |
| **Total** | **750,300** | **0** | **0** |

These are parameter configurations, **not independent statistical trials**.
This rejects only the specified models with an unchanged prefix—not unknown
seeds, early edits, different draw schedules, longer/changing keys or another
transposition.

### Positive controls and an offset ambiguity

Four synthetic examples, one per draw API, had unknown five-phase alphabets and
a held-out sixteen-letter marker. Training-compatible candidates predicted
**all 5,736 held-out background letters exactly**, identifying the altered span.
The marker **FINDTHEODDOBJECT is synthetic**, not a Nachtlorn recovery.

Selection used training compatibility and the resulting prediction class, not
knowledge of the answer. Native `randrange` has a genuine ambiguity: offsets
**8, 17 and 26** produced the same control stream because the earlier draws were
rejected. The three fits gave **one identical prediction**. Thus a working
predictor need not identify a unique initial raw-word offset.

## 2. Could the recovered object be packed 32/64-bit values?

The body length has a potentially useful factorization:

```text
8,736 = 1,248 × 7 = 624 × 14
```

Since 624 is MT19937's state-word count, this suggested a bounded test of packed
numeric objects rather than more prose decoding. **The factorization alone is
not evidence that a state dump was intended.**

A 32-bit integer written as seven base-26 digits can use only **14** different
most-significant digits. A 64-bit integer written as fourteen digits can use
only **8**. Five fixed, unknown alphabet permutations do not remove those bounds
within each phase.

The checker selects the best possible allowed leading-symbol subset for each
phase. Letters outside those subsets give a rigorous **lower bound** on required
symbol replacements. This is only a necessary condition: satisfying it would
not by itself prove valid integers or recover a state.

It evaluated **128 transformed readouts** and **5,376 packing conditions**:

- Raw text, reversal, and seeded forward/inverse shuffles.
- Shuffle units of **1, 5, 7, 14 or 60 letters**, using seed **4300** before any
  indent draws or after **145/146 native indent draws**.
- Optional BLOOM, BLPNM or BLNPM decryption before the route.
- Every block alignment and both digit orders, allowing five arbitrary phase
  alphabets. Incomplete edge blocks were excluded, not silently padded.
- Ragged-unit shuffles were inverted using the true length of the short unit,
  even when it had moved into the middle of the stream.

| Proposed object | Best necessary lower bound across tested readings |
|---|---:|
| Seven-digit uint32 values | **392 leading-symbol replacements** |
| Fourteen-digit uint64 values | **304 leading-symbol replacements** |

**No reading fits as valid packed objects with just one exceptional object.**
One exceptional fixed-width object could affect only one leading symbol; even
the best reading requires hundreds. This does not reject a different encoding,
an unknown route, additional masking, or insertion/deletion shifts.

### Independent verification

Synthetic packed objects survived unknown phase alphabets, a seeded ragged-unit
shuffle and a Vigenere layer. The search found both a legal population and the
same population with one interior out-of-range object, with bounds **0 and 1**
respectively. The interior placement prevents an alignment from hiding the
control's outlier in an excluded edge block.

Every one of the **5,376 actual capacity cases** was independently replayed using
integer histograms and position-index routes rather than the production
Counter/chunk implementation. The complete case digest matched:

```text
17a7771fcc3e7c9ade38d10dd9518a4e4e32cf28adcf6843529311baaa0d3ad9
```

## What this changes

The tested block generators do not supply a predictable background against
which a planted word can be identified. The tested numeric packings do not
supply a recovered population with one exceptional member either.

The **construction → recovered population → outlier** bridge remains missing.
Neither FRODO nor TRACT gains new confirmation from these negative tests. No
spelling repair, missing page, or extra unconfirmed encryption is assumed.

## Reproduce and inspect

The scripts use only the standard library. Current source and compact outputs
are kept in the repository; large generated datasets are not required.

- [Whole-block probe](../scripts/packed_block_probe.py)
- [Packed-object capacity checker](../scripts/nachtlorn_state_packing.py)
- [Native-seed results and four controls](data/nachtlorn-packed-native.json)
- [Named-seed results](data/nachtlorn-packed-named.json)
- [Seven/fourteen-width supplement](data/nachtlorn-packed-7-14.json)
- [Packed-object results](data/nachtlorn-state-packing.json)
- [Original source and provenance](nachtlorn-clue-ledger.md#reproducible-source-and-audit)

```bash
python3 scripts/packed_block_probe.py docs/data/nachtlorn-transcript.txt \
  --seed-int 4300 --controls
python3 scripts/nachtlorn_state_packing.py docs/data/nachtlorn-transcript.txt
python3 -m unittest tests.test_packed_block_probe tests.test_nachtlorn_state_packing
```

**At this construction checkpoint, 83 targeted tests passed**, including 21 new tests for native draw/digit oracles,
held-out isolation, unknown symbols, prediction-equivalent offsets, exact capacity
bounds, ragged-route inverses and full independent actual-case replay. The
original source SHA-256 remains unchanged.
