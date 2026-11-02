# The other two Ulysses running-key arithmetic directions

**R29: the direct K−C and C+K readings also have negative training scores at
every eligible book offset under the fixed English monogram profile.** This is
a bounded cryptanalytic screen, not a recovered plaintext or final outlier.

[R26](nachtlorn-book-exact-bound.md) used exact integer upper weights to bound
all 1,188,470 eligible *Ulysses* starts for `P=C−K mod 26` on the first 6,000
body letters. That model does not cover the other two conventional arithmetic
readings. R29 uses exactly the same pinned book, normalization, ciphertext,
A=0, offset eligibility and profile, but independently evaluates `P=K−C` and
`P=C+K`. They are alternatives, not consecutive cipher layers. The final I is
retained; no seed, route, word or key was chosen by output.

| Direct reading | All-offset upper bound, mean nats/letter | First maximum offset | All negative? |
|---|---:|---:|---|
| C−K, earlier R26 | −0.5290945 | 365,346 | Yes |
| K−C, R29 | −0.5221000 | 359,675 | Yes |
| C+K, R29 | −0.5156193 | 919,862 | Yes |

The new worker sums 6,000 integer upper weights for **each** of the 1,188,470
eligible offsets and **each** of the two signs. Because every weight strictly
exceeds the corresponding true likelihood ratio times 1,000, every actual
score is below its listed upper bound. Both recorded maximum-score offsets are
independently re-evaluated with scalar Python.

The result excludes only a **positive training monogram score** in these direct
models. It does not show that all English text must have a positive score,
exclude an embedded short message, test the held-out suffix for every offset,
identify a key, or rule out another use of the book, additional processing or a
non-prose object. The [historical book search](nachtlorn-analysis.md#follow-up-bloom-as-a-possible-ulysses-reference)
already checked all three signs with a 120-character ranking; the present
6,000-character bound is a distinct follow-up, not an independent clue or a
claim that those signs were never tested.

## Reproducibility and controls

- [Registration and outcome](data/nachtlorn-reset-plan.json)
- [Numerical result](data/nachtlorn-book-sign-bounds.json)
- [Python driver](../scripts/nachtlorn_book_sign_bounds.py),
  [native worker](../scripts/nachtlorn_book_sign_worker.cpp) and
  [tests](../tests/test_nachtlorn_book_sign_bounds.py)
- [R26 weight proof and pinned-source details](nachtlorn-book-exact-bound.md)

Four tests independently compare every worker score with scalar arithmetic on
small cases, recover synthetic messages for both signs, check inputs and
overwrite guards, and replay both actual maximum witnesses. The synthetic
messages are controls, not puzzle content. The single actual-source run used
`g++` 12.2.0 with `-O3 -std=c++17 -Wall -Wextra -Werror`; the binary hash is in
the result. **341 tests across 43 research modules passed** locally with prior
optional dependencies installed; whole-repository Ruff passed. The worker
requires a C++17 compiler, not NumPy or a solver.

The source transcript remains unchanged, SHA256
`04eddf97e8ebbc9ce2565269508d63c99b60efc7cacf3f2c020f14215dc67e7e`.
The book remains the pinned ignored scratch copy, SHA256
`4ea566a510a547adcb01b52fe78ff269926fe8d5e8060591f725de6d77afa3ac`.

```bash
g++ -O3 -std=c++17 -Wall -Wextra -Werror scripts/nachtlorn_book_sign_worker.cpp \
  -o scratch/nachtlorn_book_sign_worker
python3 scripts/nachtlorn_book_sign_bounds.py docs/data/nachtlorn-transcript.txt \
  --book scratch/nachtlorn-ulysses4300.txt --worker scratch/nachtlorn_book_sign_worker \
  --output scratch/nachtlorn-book-signs-replay.json
python3 -m unittest tests.test_nachtlorn_book_sign_bounds -v
```
