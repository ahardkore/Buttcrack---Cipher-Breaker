# Exact upper-bound check for the Ulysses running-key scan

**R26: every eligible offset fails a positive training-score screen under the
registered direct running-key model.** This strengthens the previous numerical
scan, but it does not recover plaintext or an outlier.

## What changed

[R25](nachtlorn-book-fullscan.md) numerically ranked all **1,188,470** eligible
book starts on the first 6,000 ciphertext letters. Its top training candidate
failed a separate held-out screen. Because the ranking used floating-point
FFTs, and because only one held-out candidate was screened, that result did not
prove that all offsets failed any held-out test.

R26 checks a different, explicit statement about the **training prefix**. It
uses the same fixed English monogram profile, same whole-file ASCII-normalized
book, full 8,736-letter body, A=0, and `P=(C−K) mod 26`. The key is a contiguous
forward segment of the pinned Gutenberg book, starting at any location with room
for the full body. No other arithmetic, key alignment or cipher is searched.

For each plaintext glyph, the checker constructs an integer `w` such that
`w / 1000` is strictly **above** that glyph's natural-log likelihood ratio
against a uniform alphabet. It uses exact integer frequency parameters and
80-digit Decimal logarithms; each upper bound is independently checked by a
high-precision exponential with a safety margin. A C++ worker then sums these
integer upper weights for each of the 6,000 decoded letters at **every eligible
start**, and finds the maximum using integer arithmetic.

## Result

| Check | Result |
|---|---:|
| Eligible book offsets | 1,188,470 |
| Integer additions across offsets | 7,130,820,000 |
| Largest upper-bound sum | −3,174,567 |
| Largest upper bound per letter | **−0.5290945 nats** |
| First offset attaining that bound | 365,346 |

Thus every actual training score for this model is **below −0.5290945**, and
in particular below zero and the +0.10 threshold used for the R25 held-out
screen. The extremal integer-bound offset agrees with the R25 FFT-selected
training offset. This is a strengthening of the **training** result, not a
claim that all offsets were checked against the held-out criterion. The direct
score of the recorded bound witness is independently replayed in Python.

A score below zero means that, on this monogram profile, the prefix favors the
uniform baseline over the fixed English distribution. It is not a mathematical
proof that the prefix cannot be English: atypical English, short planted
answers, non-English intermediate layers and non-prose objects remain open.
The method does not test other Vigenère signs, key arrangements, book editions,
transpositions or additional processing. It does not disprove the book clue.

## Validation and provenance

- [Registration and outcome](data/nachtlorn-reset-plan.json)
- [Integer result, weights and source hashes](data/nachtlorn-book-runningkey-exact-bound.json)
- [Python driver](../scripts/nachtlorn_book_exact_bound.py),
  [native worker](../scripts/nachtlorn_book_bound_worker.cpp) and
  [tests](../tests/test_nachtlorn_book_exact_bound.py)

Six tests validate all 26 bounds against an independent floating calculation;
compare every native score against scalar Python on multiple small exhaustive
cases; test ties, boundary offsets and a synthetic English-like running-key
control; guard input overwrites; and replay the actual maximum witness and its
agreement with R25. The optional synthetic message is not puzzle text. The exact
integer scan is a **single actual-source run**; its compiler was `g++` 12.2.0
with `-O3 -std=c++17 -Wall -Wextra -Werror` and the binary SHA is recorded.

**327 tests across 40 research modules passed** locally, with the prior optional
book, NumPy and research solver dependencies available. Whole-repository Ruff
passed. R26 requires a C++17 compiler but no solver or NumPy. No prior solver
UNKNOWN was changed or rerun.

The source transcript remains 11,129 bytes, SHA256
`04eddf97e8ebbc9ce2565269508d63c99b60efc7cacf3f2c020f14215dc67e7e`;
the pinned book's SHA256 is
`4ea566a510a547adcb01b52fe78ff269926fe8d5e8060591f725de6d77afa3ac`.
Neither input was modified.

```bash
g++ -O3 -std=c++17 -Wall -Wextra -Werror scripts/nachtlorn_book_bound_worker.cpp \
  -o scratch/nachtlorn_book_bound_worker
python3 scripts/nachtlorn_book_exact_bound.py docs/data/nachtlorn-transcript.txt \
  --book scratch/nachtlorn-ulysses4300.txt --worker scratch/nachtlorn_book_bound_worker \
  --output scratch/nachtlorn-book-bound-replay.json
python3 -m unittest tests.test_nachtlorn_book_exact_bound -v
```
