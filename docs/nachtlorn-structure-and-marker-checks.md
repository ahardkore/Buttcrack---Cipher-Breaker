# Nachtlorn — hidden relationships and the terminal-I boundary

**Unresolved. No accepted plaintext, construction, or final outlier.** These tests
do not establish FRODO or TRACT as the answer. The original transcript is unchanged.

## 1. Higher-order modular relationships

Previous whole-base26 residue tests use particular fixed digit weights. The new
`scripts/nachtlorn_modular_words.py` instead searches every nonzero linear
functional of five letter positions, modulo nonzero scalar multiples, over
F2 and F13. There are 31 and 30,941 directions respectively. The 1,747 complete
printed groups are used; the final singleton I is explicitly retained as an
unconsumed tail in the report, not silently treated as a full group.

Three digit alphabets were tested: standard A0, BLOOM-keyed, and NACHTLORN-keyed.
The score is the Pearson histogram statistic, used as a **score, not a chi-square
p-value**. Fixed positionwise Caesar shifts just relabel histogram residues, so
ordinary five-period Vigenere need not be guessed separately for this test.

| Alphabet | Largest score over both fields | Shuffled maxima at least as large / 31 |
|---|---:|---:|
| Standard | 42.096165 | 23 |
| BLOOM-keyed | 49.820263 | 1 |
| NACHTLORN-keyed | 39.417287 | 29 |

The same within-column permutations were shared across alphabets and fields.
Across the **whole three-alphabet family, 5/31** shuffled maxima were at least
49.820263. The seemingly better BLOOM-only result is therefore not isolated as
evidence. This conditional comparison is not a correction for all prior searches.
No direction produced a one-group exception to a shared exact residue.

Results: [standard](data/nachtlorn-modular-standard.json),
[BLOOM](data/nachtlorn-modular-bloom.json),
[title](data/nachtlorn-modular-title.json),
[joint calibration](data/nachtlorn-modular-family.json).

## 2. Arbitrary secret letter mappings at every position

The stronger exact test does not assume any of those digit alphabets. For a block
of width w it uses a one-hot vector with 26w coordinates: one indicator for every
position/letter pair. A function of the form

```text
f0(letter0) + f1(letter1) + ... + f[w-1](letter[w-1]) mod q
```

is then a linear functional, even if every position has a different unknown
letter-to-number function. If exactly one block breaks an otherwise constant
checksum, deleting that block lowers the matrix rank: the block is a row-matroid
**coloop**. The native worker finds all such rows, rather than guessing mappings.
Any reported exception gets a checksum witness that Python independently replays
as zero on every other row and one on that row.

Widths 5, 7 and 14, **every phase**, and q=2/13 give 52 systems. All have the full
possible one-hot ranks, **126 / 176 / 351**, and **zero coloops**. Repeating the
52 systems after removing only the terminal I also gives full ranks and zero
coloops. Binary ranks are additionally replayed using Python integer bitsets.

This excludes a single erroneous block under this **exact additive-checksum
model**, including arbitrary per-position substitutions. It does not exclude
noisy numerical data, nonlinear relations, different groupings or other layers.

Controls use two synthetic hidden-alphabet constructions with a planted exception
at index137, plus an independent bipartite-graph rank/bridge oracle and sample/
letter/column relabeling checks. Their words and alphabets are invented test data.

Results: [width5](data/nachtlorn-additive-width5.json),
[width7](data/nachtlorn-additive-width7.json),
[width14](data/nachtlorn-additive-width14.json),
[terminal-I extraction](data/nachtlorn-terminal-i-additive.json).

## 3. Remove only the last I before binary recovery

This is distinct from the previous remove-all-I/base25 hypothesis. Appending one
base26 digit changes every byte of a whole-number decode, so a literal marker
outside the encoded body is a necessary separate boundary test. The derived
input has **8,735 letters**, while the unchanged original still has 8,736.
Both the original file hash and the exact extraction are recorded.

The two primary binary families again test 5,501 nominal clue-key/route paths,
six alphabets, whole/block packing and both byte orders:

| Order | Worker-local byte buffers | Compression attempts | Accepted objects |
|---|---:|---:|---:|
| Key then route | 60,528 | 336,634 | 0 |
| Route then key | 57,600 | 321,119 | 0 |

All **90** recorded magic-header buffers have been reconstructed and hash-checked
in a permanent regression test; none validates. Four pinned Ulysses preset
dictionary variants were supplied, with no dictionary-ID matches.

The single-letter-stage byte family also tested upper/lowercase clue keys:
149,328 mask configurations, 186 prefix-selected, no object or long UTF8 candidate.
The seven book-derived byte keys add 161,040 configurations and 218 selected,
again without an accepted object or long text. These families overlap earlier
identity/shift cases; their counts are not globally unique independent models.

The headerless numeric screen on the same terminal-I extraction produced zero
flags; maxima were **5.604293 / 5.815230**, below the declared threshold8.
This remains the heuristic screen described in the
[earlier numeric continuation](nachtlorn-numeric-continuation.md), not exhaustive
numeric decoding.

Results: [key then route](data/nachtlorn-terminal-i-key-route.json),
[route then key](data/nachtlorn-terminal-i-route-key.json),
[clue byte keys](data/nachtlorn-terminal-i-byte-layer.json),
[book byte keys](data/nachtlorn-terminal-i-book-byte-layer.json),
[numeric key then route](data/nachtlorn-terminal-i-numeric-key-route.json),
[numeric route then key](data/nachtlorn-terminal-i-numeric-route-key.json).

## 4. Authenticated modern encryption endpoint

Random-looking decoded bytes need not have file signatures. A separate bounded
probe tested AES-GCM, AES-EAX, and ChaCha20-Poly1305, including 24-byte XChaCha
nonces. Every acceptance requires a **valid 16-byte authentication tag**, not a
printability score.

It uses 18 explicit clue/book passwords; SHA256, its first16 bytes, MD5, and
NUL-padding to 16/32 bytes yield 90 distinct key materials. It tests an identity
letter stage or minus/plus/Beaufort with each of the four clue keys at phase0,
six whole-base26 alphabets, both byte orders, and both full/terminal-I inputs.
There are 26 letter paths and 312 distinct byte buffers.

The packet layouts are nonce/ciphertext/tag and nonce/tag/ciphertext, with empty
associated data. The declared nonce lengths and exact password/derivation list
are in the result. **213,408 authentication attempts yielded zero valid tags.**
No general password search, salted KDF, transposition, other packet framing or
unauthenticated mode is claimed.

Synthetic tests authenticate every declared mode/layout, reject corruption, and
recover a full terminal-marker/Vigenere/base26/AES-GCM/gzip/JSON fixture. That
fixture is solely a control; it is not a proposed recovered puzzle pipeline.

Result: [AEAD](data/nachtlorn-aead-results.json).

## Reproduction and validation

```bash
g++ -std=c++17 -O3 -Wall -Wextra -Werror \
  scripts/nachtlorn_modular_word_probe.cpp -o scratch/nachtlorn_modular_word_probe
g++ -std=c++17 -O3 -Wall -Wextra -Werror \
  scripts/nachtlorn_additive_word_probe.cpp -o scratch/nachtlorn_additive_word_probe
python3 scripts/nachtlorn_modular_words.py docs/data/nachtlorn-transcript.txt \
  --worker scratch/nachtlorn_modular_word_probe --alphabet standard --nulls 31 \
  --output scratch/modular-standard.json
python3 scripts/nachtlorn_additive_words.py docs/data/nachtlorn-transcript.txt \
  --worker scratch/nachtlorn_additive_word_probe --width 5 --output scratch/additive5.json
python3 scripts/nachtlorn_binary_research.py docs/data/nachtlorn-transcript.txt \
  --mode periodic-then-route --drop-final-i \
  --dictionary scratch/nachtlorn-ulysses4300.txt --output scratch/terminal-binary.json
python3 scripts/nachtlorn_numeric_probe.py docs/data/nachtlorn-transcript.txt \
  --mode periodic-then-route --drop-final-i --output scratch/terminal-numeric.json
python3 -m pip install --target scratch/nachtlorn-crypto-deps pycryptodome==3.23.0
PYTHONPATH="$PWD/scratch/nachtlorn-crypto-deps" python3 scripts/nachtlorn_aead_probe.py \
  docs/data/nachtlorn-transcript.txt --output scratch/aead.json
```

Other alphabets, widths and transform orders use the corresponding CLI choices.
The trimmed additive and book-byte results use the same public `scan` APIs with
`source[:-1]`; the book-key list is unchanged from the previous numeric report.
Book and optional crypto dependencies stay in ignored scratch storage; no
application dependency or original tracked source was changed.

**146 targeted tests pass**, including the two trusted native workers, replay of
all 90 new signature buffers, marker extraction, and optional AEAD tests with
PyCryptodome3.23.0 installed privately. No recovered content was executed.

A fresh gist retrieval still has one revision, zero comments and unchanged
SHA256 `04eddf97e8ebbc9ce2565269508d63c99b60efc7cacf3f2c020f14215dc67e7e`.
All workers finished. None of these negatives licenses calling the puzzle
unsolvable or presenting a candidate word as a verified answer.
