# Nachtlorn — fieldwise tables and explicit poem-key instructions

**Unresolved. No decoded population or final outlier.** This continuation tests
three separately registered hypotheses, not a succession of encryption layers.
Original wording, body letters, spaces and terminal I remain untouched.

## R8: per-field encoding, rather than one large base26 integer


**Later exact follow-up:** [R18 field-capacity certificates](nachtlorn-field-capacity.md)
exclude this **raw** fixed-width schema under every fixed bijective digit alphabet,
not just the selected alphabets below. The later scope also includes reversed
within-field digit order; it does not extend the exclusion to intervening letter
transforms, other encodings or IBLTs generally.

The [pinned C++ reference](data/nachtlorn-iblt-reference-source.json) supplies
logical count32/key64/checksum32 fields and permits zero-length values. It does
**not** supply the letter encoding below or attribute any implementation to the
puzzle author.

A minimal fixed-width A0 encoding requires:

```text
count32        7 letters
key64         14 letters
checksum32     7 letters
cell total    28 letters
```

The full 8,736-letter body fits **312** such cells, divisible into four hash
partitions. This is a mathematical fit, not independent evidence of an IBLT.
Removing the final I breaks this exact fit; no missing letter was manufactured.

The registered test used row-interleaved or field-major arrays, most-significant
letter first, signed32 two's-complement counts bounded by 1,000,000, and no header
or value payload. Raw letters and the already admitted phase-zero operations for
BLOOM/GLOOM/WLOOM were considered separately.

**Result: 40 configurations; zero validated tables.** Twenty final-I-removed
cases fail dimensions. All twenty full-body cases fail field constraints. For
example, the unmodified interleaved reading has **145 overflowing count fields,
213 overflowing key fields and 154 overflowing checksum fields**. Its remaining
167 count fields also exceed the registered signed-count bound. Bit patterns were
not truncated to make them fit.

[Fieldwise result](data/nachtlorn-reset-fieldwise-iblt-results.json).

### Independent implementation validation

Unlike a dimension/stripe check, this probe includes a complete key-only validator:
MurmurHash3 checksum seed11, four partitioned hash positions, signed peeling,
empty residual across **all** partitions, and exact reconstruction from recovered
keys. Even validation would establish only numeric keys, not their meaning or a
puzzle outlier. Empty tables are recognized without calling them solutions.

Before testing the puzzle, a synthetic C++ oracle was compiled from the reviewed,
pinned reference. It agrees on **20 hash vectors, 24 table cells, positive and
negative entries, cancellation and complete recovery**. Additional tests reject
corrupt checksums, pure cells in the wrong buckets, residuals outside the first
partition, integer overflow and count-bound violations. Both letter layouts and
a repeating-key/terminal-marker control recover synthetic tables exactly.

[Independent oracle results](data/nachtlorn-fieldwise-iblt-oracle.json).
The original reference lacks a required size-type include; compilation supplies
`-include stddef.h` without altering its pinned bytes. No recovered code or puzzle
content is executed.

## R9: explicitly apply given/taken to the two O initials

This is an alternative instruction hypothesis, not an author-confirmed rule:

| Colour reading | Before unit shifts | O given one / O taken one |
|---|---|---|
| green contents | GLOOM | **GLPNM** |
| white vessel | WLOOM | **WLPNM** |
| unchanged baseline | BLOOM | **BLPNM** |

Line3's initial O is increased to P; line4's O is decreased to N. L and M remain
unchanged by hypothesis. The strings in the last column are **derived keys**, not
literal acrostics of a corrected poem. No direction swap, extra phase or further
letter edit was tried.

BLPNM was proposed before the reset. It is included only as the declared mechanical
baseline, **not rediscovered evidence** and not a reason to accept historical word
fragments. The new colour-combined keys are GLPNM and WLPNM.

Each key received the same separate repeating-letter-key and standalone
password tests used for R5/R6, never one after the other. In total: **18 letter
paths / 576 packet configurations, zero complete registered objects; 21,888
authentication attempts, zero valid tags**. Direct letter
prefixes are also not readable prose; this is an observation, not the acceptance
criterion. Synthetic structured and authenticated controls pass for the new keys.

[Poem-key results](data/nachtlorn-reset-poem-key-results.json).

## R10: the new strings as byte keys instead

A distinct key role tested direct repeated byte XOR of the raw whole-base26 body,
**without a prior letterwise transformation**. The four new strings GLOOM,
WLOOM, GLPNM and WLPNM each use upper/lower/title case and raw ASCII or SHA256
raw-digest material. Old BLOOM/BLPNM byte-key grids were not repeated.

Across the existing **64** byte representations this gives **1,536 XOR trials**.
There are **zero complete structured objects, whole-printable-ASCII candidates,
or origin-zero NPY/SQLite diagnostic signatures**. A signature would require
further validation, not count as a decoded object. A synthetic gzip/JSON control
recovers exactly and rejects truncation.

[Byte-key results](data/nachtlorn-reset-colour-byte-results.json).

## What these results change

The fieldwise IBLT interpretation fails stronger predictions than divisibility.
The explicit given/taken key rule has now been tested together with the user's
colour replacement, rather than stopping at GLOOM. Direct byte-key use was also
checked, without stacking ciphers to rescue a failed model.

None recovers an object population. They reject only the declared encodings and
key roles, not the book association, every IBLT, or the existence of a solution.
The earlier black-bowl/**mourning** reading still leaves BLOOM intact. There is
no body-recovery evidence selecting GLOOM, GLPNM or a particular colour correction.
No repaired source, preferred word or final-outlier claim is introduced.

## Reproduce

```bash
export PYTHONPATH="$PWD/scratch/nachtlorn-crypto-deps${PYTHONPATH:+:$PYTHONPATH}"
python3 scripts/nachtlorn_fieldwise_iblt_probe.py docs/data/nachtlorn-transcript.txt \
  --output docs/data/nachtlorn-reset-fieldwise-iblt-results.json
python3 scripts/nachtlorn_poem_key_probe.py docs/data/nachtlorn-transcript.txt \
  --book scratch/nachtlorn-ulysses4300.txt \
  --output docs/data/nachtlorn-reset-poem-key-results.json
python3 scripts/nachtlorn_colour_byte_probe.py docs/data/nachtlorn-transcript.txt \
  --output docs/data/nachtlorn-reset-colour-byte-results.json
python3 -m unittest tests.test_nachtlorn_fieldwise_iblt_probe \
  tests.test_nachtlorn_poem_key_probe tests.test_nachtlorn_colour_byte_probe
```

Only the authentication tests require the existing optional PyCryptodome research
dependency. Missing crypto is explicitly marked untested. The fieldwise validator
and byte-XOR probe use the standard library.

Rebuild the independent synthetic oracle after obtaining the pinned references:

```bash
g++ -std=c++17 -O2 -Wall -Wextra -Werror -Wno-implicit-fallthrough \
  -include stddef.h -I scratch/nachtlorn-iblt-reference \
  tests/fixtures/nachtlorn_iblt_oracle.cpp \
  scratch/nachtlorn-iblt-reference/iblt.cpp \
  scratch/nachtlorn-iblt-reference/murmurhash3.cpp \
  -o scratch/nachtlorn-iblt-oracle
scratch/nachtlorn-iblt-oracle
```

Verification: **198 research tests pass across 24 modules**; **475 Python files**
parse successfully. R5–R10 results replay, original source/book/archive hashes,
all eleven pinned reference files, plan IDs, links and the fixed branch pass
audits. A fresh gist check still has one revision, zero comments and exactly the
original transcript SHA256; no newer author material was found there.
