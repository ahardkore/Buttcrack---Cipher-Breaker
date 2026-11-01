# Nachtlorn — binary envelopes and byte-layer recovery

**Status: unresolved. No verified payload or final outlier recovered.**

This round tested a different recovery bridge:

```text
clue-key/route reversal → base-26 binary decoding → decompression or parsing
                     → identify the recovered object → select its outlier
```

That is a hypothesis, not a recovered pipeline. It addresses the author's
reported distinction between encryption, construction and interpretation.
**No English n-gram gate or preferred answer word was used.** Every original
letter, including the final singleton I, was retained.

## 1. Letter transforms followed by binary recovery

The first two workers tested one optional periodic operation and one optional
route, in both orders:

- **97 periodic settings:** identity, plus Vigenere subtraction/addition,
  Beaufort and Porta with BLOOM, BLPNM, BLNPM or NACHTLORN at every key phase.
- **29 routes:** identity/reversal; columnar and Myszkowski with those keys;
  rail fence with 2–8 rails at offset zero; forward/inverse seed-4300 shuffles
  of 1-, 5- or 60-letter units, before or after all 146 native indent draws.
- Six numeric alphabets: A=0, bijective A=1, I=0, reversed alphabet, and keyed
  alphabets derived from BLOOM/NACHTLORN.
- Whole-stream integers and fixed base-26 blocks of 5→3, 7→4 or 14→8 bytes,
  with both byte orders. Overflow rejects a packing rather than truncating it.
  A short final block is explicitly retained as a minimal-byte integer.

The parsers checked complete JSON, complete binary-pickle **syntax only**,
readable ZIP members, and checksum-validated gzip/zlib/bzip2/XZ members, including
members embedded inside decoded buffers. Magic headers alone were recorded,
**not counted as recoveries**.

| Recovery order | Path configurations | Buffers inspected after worker-local de-duplication | Accepted objects |
|---|---:|---:|---:|
| Periodic operation → route → binary | 2,813 | 60,528 | **0** |
| Route → periodic operation → binary | 2,688 | 57,600 | **0** |

There are **5,501 nominal paths**. The two buffer counts are not a globally
unique count: equivalent transformations can occur across workers. These are
bounded configurations, not independent statistical trials.

### Could Ulysses be a compression dictionary rather than the cipher key?

Because BLOOM and the exact layout seed point toward *Ulysses*/4300, the workers
also tested zlib preset-dictionary IDs from the previously identified book:

| Dictionary bytes | Adler-32 ID |
|---|---|
| Original UTF-8 book | `4676cc5d` |
| Its last 32,768 bytes | `94cab4ce` |
| ASCII letters only, uppercase | `3390d06c` |
| Last 32,768 bytes of that letter stream | `f38efa17` |

**No tested header requested any of these IDs.** This tests only this archived
edition and these four dictionary variants, not every possible literary key.

The source is pinned to Git blob
`b2300b64c6517c83b5a367943448b1c0208d813f`, 1,580,890 bytes, SHA-256
`4ea566a510a547adcb01b52fe78ff269926fe8d5e8060591f725de6d77afa3ac`.

## 2. A byte-level cipher between base-26 and the recovered object

A separate, smaller family allowed **at most one letter operation**—identity,
one periodic setting, or one route—before binary decoding. It then tried:

- Identity byte mapping.
- Repeating XOR with each of the four clue keys at every byte phase.
- Uniform +1 or −1 byte shifts, modulo 256.

These are **27 byte mappings**, not confirmed poem instructions. The family
covered **125 nominal letter paths**, producing 2,928 distinct base buffers and
**79,056 byte-mapping configurations**.

A 128-byte prefilter required a possible object header at offset zero or a
mostly printable UTF-8 prefix. Partial final UTF-8 characters were handled
without discarding the candidate. **99** configurations passed that filter.
Their complete results were inspected for envelopes and for language-independent
text of at least 64 characters with at least 98% printability.

**Result: zero accepted envelopes and zero long-text candidates.** The text test
could have found CSV, lists of numbers or other non-prose text; it did not require
English words. It was not applied to every two-letter-operation path above.

Across all three final runs there were **661,796 wrapped-stream attempts**.
Headers that failed decompression/checksums did not become answer candidates.
Reruns used to correct header handling and retain the full header evidence are
not counted as additional search configurations.

### All header evidence rechecked

All **121** recorded signature-hit buffers were reconstructed from their saved
paths and hash-checked: **57 gzip, 56 bzip2 and 8 JPEG signatures**. None yielded
a validated member. Each JPEG coincidence declares a first segment longer than
the remaining buffer, so none is a complete JPEG image. The
[header audit](data/nachtlorn-binary-header-audit.json) records those checks, and
a regression test replays all 121 buffers without the external book scratch file.
The evidence limit was not reached; no later header was hidden behind the first
few failed examples.

## Controls and safety

**114 targeted tests pass**, including 31 new tests for this continuation.
Four full-path synthetic examples demonstrate recovery without English scoring:

1. Numeric JSON → gzip → keyed base-26 → Myszkowski → phase-shifted Porta.
2. Numeric JSON → dictionary-zlib → bijective/little-endian base-26 → Vigenere
   → a seeded ragged-unit shuffle.
3. Numeric JSON → gzip → clue-key byte XOR → base-26 → columnar transposition.
4. Uncompressed CSV → byte shift → I=0 base-26 → a periodic letter operation.

**Those are synthetic controls, not Nachtlorn plaintext.** Exact payload hashes
were checked only after candidate discovery. The tests also cover corrupt or
truncated streams, byte/digit oracles, all transform inverses, partial blocks,
and overlapping zlib headers. In particular, a false header at offset zero must
not hide a genuine overlapping member at offset one.

Recovered content was **never executed**. Pickle was statically inspected with
`pickletools`, never loaded. ZIP members were read in memory, never extracted.
Decompression was capped at **1 MiB**, and XZ memory at **64 MiB**. The caps and
supported formats are part of the test's limits, not proof that larger or
unsupported objects are absent.

## What remains open

This provides no verified compressed/serialized object from which to select an
outlier. It neither confirms FRODO/TRACT nor justifies repairing either fragment.
The only exact generator fit remains the **146 seed-4300 indentation values**.

Unknown keys, additional/different masks, other encodings, larger objects and
other routes remain outside these tests. The byte-layer family also does not
cover two letter operations plus a byte mask, or arbitrary masked prefix offsets.

## Reproduce and inspect

- [Envelope/decoder implementation](../scripts/binary_envelope_probe.py)
- [Language-independent text and byte mappings](../scripts/binary_text_probe.py)
- [Path search and preset dictionaries](../scripts/nachtlorn_binary_research.py)
- [Key-then-route results](data/nachtlorn-binary-key-route.json)
- [Route-then-key results](data/nachtlorn-binary-route-key.json)
- [Byte-layer results](data/nachtlorn-binary-byte-layer.json)
- [Pinned book/dictionary provenance](data/nachtlorn-binary-book-source.json)
- [Exact puzzle source](data/nachtlorn-transcript.txt)

The book remains an ignored scratch input, not a copied dataset in Git. Recreate
it using the pinned public blob if the scratch file is unavailable:

```bash
mkdir -p scratch
gh api repos/GITenberg/Ulysses_4300/git/blobs/b2300b64c6517c83b5a367943448b1c0208d813f \
  --jq .content | base64 -d > scratch/nachtlorn-ulysses4300.txt

python3 scripts/nachtlorn_binary_research.py docs/data/nachtlorn-transcript.txt \
  --mode periodic-then-route --dictionary scratch/nachtlorn-ulysses4300.txt
python3 scripts/nachtlorn_binary_research.py docs/data/nachtlorn-transcript.txt \
  --mode route-then-periodic --dictionary scratch/nachtlorn-ulysses4300.txt
python3 scripts/nachtlorn_binary_research.py docs/data/nachtlorn-transcript.txt \
  --mode byte-layer --dictionary scratch/nachtlorn-ulysses4300.txt
```

All current scripts, tests and compact results are archived with the source.
No source spelling, indentation or ciphertext letter was changed.
