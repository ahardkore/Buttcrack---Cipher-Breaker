# Nachtlorn — raw numeric and remove-I continuation

**Still unresolved. No plaintext, construction, or final outlier was recovered.**
FRODO and TRACT remain unverified candidates, not established answers. This is a
record of bounded follow-up tests, not another claimed solution.

## Headerless numeric endpoint

`scripts/nachtlorn_numeric_probe.py` reuses the 5,501 clue-key/route paths from the
[binary investigation](nachtlorn-binary-recovery.md), but tests whole-integer
base-26 output for numeric structure rather than file signatures. It uses the
same six digit alphabets. Byte reversal only permutes the screened lanes.

Each lane has at least 64 observations. Periods are 2, 4, 8, 20, 36, 40 and 72;
the screen tests eight individual bits and the parity of bits 5 and 6. The latter
captures an IEEE exponent relation that individual balanced bit marginals can
miss. Its score is `abs(2*ones-n)/sqrt(n)`, with a threshold of 8. **This is a
structural heuristic, not a calibrated p-value.**

| Transform order | Paths | Worker-local distinct byte profiles | Largest score | Flags |
|---|---:|---:|---:|---:|
| Periodic then route | 2,813 | 15,132 | 5.577874 | 0 |
| Route then periodic | 2,688 | 14,400 | 5.303301 | 0 |

No actual buffer reached the numeric interpreter. For flagged buffers that
interpreter would test 27 byte masks, both reversals, offsets 0–31, float32/64,
and both endian interpretations. Its trial criterion requires all but at most
one value finite and either zero or magnitude 1e-12–1e12, and exactly one value
outside the quartiles' three-IQR fences. Neither this rule nor this datatype is
confirmed by the author.

Four synthetic bias controls pass. A separate regression catches finite floats
with deliberately balanced single-bit marginals using exponent parity. A numeric
interpreter regression recovers the planted index431/value37 from a Gaussian
fixture. **The fixture's `NACHTLORN` header, count640, and outlier are invented
control data, not recovered puzzle content.** The dimensional coincidence
5,133 = 13 + 640×8 is not evidence for that format.

Results: [key then route](data/nachtlorn-numeric-key-route.json),
[route then key](data/nachtlorn-numeric-route-key.json).

## Remove-I followed by base25

The user's remove-I suggestion was also tested as a binary extraction hypothesis:

- Literal removal: 8,736 letters become 8,411 letters; no source bytes are edited.
- Remove I, then optional mod25 minus/plus/Beaufort using the four existing clue
  keys and every phase; or apply one existing mod26 periodic operation first,
  then remove I. There are 169 explicit paths.
- Six no-I base25 alphabets, whole-integer packing, both byte orders, and 27 byte
  masks: 2,028 byte buffers and 54,756 mask configurations.
- Original unmasked buffers get full binary inspection; other masks use the
  existing origin-header/printable-prefix gate. Four pinned Ulysses dictionary
  variants are available. Each big-endian buffer also gets the numeric screen.

**No validated object, long UTF8 candidate, or numeric flag resulted.** The script
has 30 independent integer/Horner oracles and an inserted-I, mod25 BLOOM,
base25, gzip positive control. Removal remains a hypothesis, not a lossless
source correction or an established layer.

Results: [base25](data/nachtlorn-base25-results.json).

## Literal lowercase and book-derived byte keys

The printed acrostic is lowercase `bloom`; bytewise XOR is case-sensitive even
though the letter ciphers normalize case. The existing byte-layer scanner now
accepts explicit byte keys without changing its original defaults. Two further
families used the original 125 single-letter-stage paths and 2,928 byte buffers:

| Byte keys | Mask configurations | Prefix-selected | Validated objects | Long UTF8 candidates |
|---|---:|---:|---:|---:|
| Lowercase versions of the four clue keys | 79,056 | 113 | 0 | 0 |
| `4300`, `ULYSSES`, `ulysses`, `JOYCE`, `joyce`, `LEOPOLDBLOOM`, `leopoldbloom` | 161,040 | 212 | 0 | 0 |

Both used all phases, identity and byte ±1, four base-26 packing modes, six
alphabets, both byte orders, and the four pinned dictionary variants. No preset
dictionary ID matched. These counts overlap previous byte families; they are
not additional globally unique inputs. The book keys are motivated hypotheses,
not confirmed keys.

Results: [lowercase](data/nachtlorn-binary-lowercase-byte-layer.json),
[book-derived keys](data/nachtlorn-binary-book-byte-layer.json).

## Reproduction and limits

```bash
python3 scripts/nachtlorn_numeric_probe.py docs/data/nachtlorn-transcript.txt \
  --mode periodic-then-route --output scratch/numeric-key-route.json
python3 scripts/nachtlorn_numeric_probe.py docs/data/nachtlorn-transcript.txt \
  --mode route-then-periodic --output scratch/numeric-route-key.json
python3 scripts/nachtlorn_base25_probe.py docs/data/nachtlorn-transcript.txt \
  --dictionary scratch/nachtlorn-ulysses4300.txt --output scratch/base25.json
python3 scripts/nachtlorn_binary_research.py docs/data/nachtlorn-transcript.txt \
  --mode byte-layer --byte-key-case lower \
  --dictionary scratch/nachtlorn-ulysses4300.txt --output scratch/lowercase.json
```

For the book-key family, call `scan(source, "byte-layer", dictionaries,
byte_keys=("4300", "ULYSSES", "ulysses", "JOYCE", "joyce", "LEOPOLDBLOOM",
"leopoldbloom"))` in `scripts.nachtlorn_binary_research`; `source` is the literal
uppercase body without spaces and `dictionaries` comes from `book_dictionaries`.
All exact masks and source hashes are in the result JSON. Book provenance is
[pinned separately](data/nachtlorn-binary-book-source.json); the full book stays
in ignored scratch storage, not in Git.

No arbitrary key search, unknown mask, general serialization search or exhaustive
numeric interpretation is claimed. The binary output and decompression caps
remain those of the earlier investigation. These negatives do not establish that
the puzzle lacks a solution, or that FRODO/TRACT is intended.

All **125 targeted tests pass**, including eleven new tests for this continuation.
The original source SHA256 remains
`04eddf97e8ebbc9ce2565269508d63c99b60efc7cacf3f2c020f14215dc67e7e`.
