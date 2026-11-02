# Ulysses running key: full-training offset scan

**R25: the best training-selected candidate fails the reserved-suffix screen.**
No plaintext, recovered population or outlier is claimed.

The previous [frequency invariant](nachtlorn-book-frequency.md) rules out a
contiguous *Ulysses* passage as the entire plaintext under only a fixed
substitution and transposition. It does not rule out the book as a **key**.
This experiment tests one explicit running-key construction, without targeting
a word or assuming that the author's final answer must be long prose.

## Fixed attack

- Book: the entire pinned Gutenberg 4300 file, retaining original ASCII letters
  and uppercasing. The file contains **1,197,205** normalized letters.
- Ciphertext: all **8,736** body letters, including terminal I.
- Key: a contiguous, nonrepeating book segment aligned to body position zero;
  test every start with room for the whole body: **1,188,470 offsets**.
- Decryption: `P = (C − K) mod 26`, with A=0. No extra cipher, changed alphabet,
  edit, reverse reading or alternative book normalization is included.
- Rank offsets using the first **6,000** decoded letters, by mean natural-log
  likelihood ratio of a fixed English monogram profile against uniform letters.
  Choose only the highest training score, with lowest offset as tie-breaker.
- Before executing on the source, require the remaining **2,736** decoded
  letters to achieve a mean likelihood ratio of at least **+0.10 nats/letter**.
  This is a fixed *screen*, not a sufficient condition for plaintext or a
  calibrated probability of authorship.

The author describes construction and interpretation layers, not necessarily
whole-body English. Consequently, failure here does not rule out a shorter
message, intermediate object, or a different use of the book.

## Result

| Measure | Result |
|---|---:|
| Offsets scored on training prefix | 1,188,470 |
| Training-selected normalized book offset, zero-based | 365,346 |
| Training score, nats per letter | −0.529595 |
| Held-out score, nats per letter | −0.633604 |
| Predeclared held-out screen | ≥ +0.10 |
| Screen passed | **No** |

Negative means the observed letter frequencies of that selected output score
worse under the fixed English profile than under uniform letters. This does not
make the selected offset a key or establish what generated the ciphertext.
The suffix was not used to select the offset. A failed top-training candidate
also **does not prove that no other offset could pass the suffix screen**: only
one candidate was evaluated by that gate. Nor would a screen pass by itself
validate prose, a recovered object, or a final outlier.

## How this differs from earlier work

The [historical book scan](nachtlorn-analysis.md#follow-up-bloom-as-a-possible-ulysses-reference)
ranked all eligible offsets using **120-character quadgram prefixes**, then
inspected the top 20 for each of three arithmetic readings. R25 instead uses
**6,000 training letters**, one arithmetic reading, a fixed independent suffix
screen and a reproducible numerical convolution. It is not a rerun of that
unchanged solver. The later eight-address structured-packet check also had a
different endpoint. These are overlapping hypotheses, not independent trials.

## Calculation and controls

For each ciphertext glyph, the checker correlates its positions in the training
prefix against the book's per-glyph likelihood weights using NumPy FFT. This
computes a numerical score for each eligible start, rather than decrypting and
scoring 7.1 billion characters one at a time. Every offset within `1e-5` of the
floating-point maximum is rescored directly, and the selected training score
and entire held-out score are recomputed in ordinary Python. The selected score's
FFT/direct error is recorded. **Floating-point ranking is not a formal exact
certificate**; numerical accuracy is checked on exhaustive small cases.

Five tests compare every FFT score to direct scoring on small cases, recover a
synthetic running-key message (including its held-out suffix), check fixed
weights and inversion, guard invalid inputs and source overwrites, and replay
the actual selected candidate independently. The synthetic 500-letter message
uses a repeated paragraph and is a computational control, not a puzzle result
or a general language benchmark. With the optional NumPy 2.2.6 and previously
installed research dependencies, **321 tests across 39 research modules passed**
locally; whole-repository Ruff passed. The book and optional dependencies are
stored in ignored scratch paths and are not application dependencies.

- [Registered design and outcome](data/nachtlorn-reset-plan.json)
- [Machine-readable result](data/nachtlorn-book-runningkey-fullscan.json)
- [Probe](../scripts/nachtlorn_book_fullscan.py) and
  [tests](../tests/test_nachtlorn_book_fullscan.py)
- [Pinned book provenance](data/nachtlorn-binary-book-source.json)

The book bytes match SHA256
`4ea566a510a547adcb01b52fe78ff269926fe8d5e8060591f725de6d77afa3ac`;
the source remains 11,129 bytes, SHA256
`04eddf97e8ebbc9ce2565269508d63c99b60efc7cacf3f2c020f14215dc67e7e`.
No source letters, spaces or line breaks were modified.

```bash
python3 -m pip install --target scratch/nachtlorn-numpy-deps numpy==2.2.6
# Restore the pinned book as described in the previous frequency report.
export PYTHONPATH="$PWD/scratch/nachtlorn-numpy-deps:$PWD"
python3 scripts/nachtlorn_book_fullscan.py docs/data/nachtlorn-transcript.txt \
  --book scratch/nachtlorn-ulysses4300.txt --output scratch/nachtlorn-book-fullscan-replay.json
python3 -m unittest tests.test_nachtlorn_book_fullscan -v
```

No solver timeout was rerun, no previously recorded UNKNOWN was reclassified,
and no historical short fragment was used for selection or validation.
