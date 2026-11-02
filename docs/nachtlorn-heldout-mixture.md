# Could a diluted English-frequency signal persist across the two pages?

**R27: the registered page-1 fit does not predict page 2.** No plaintext,
population, key or final outlier is recovered. This does not require the entire
puzzle to be prose and does not exclude a short hidden message.

## Model and independent page split

Some English-like letters could conceivably be diluted among random-looking
filler and then relabeled by one fixed substitution. The tested statistical
model assigns each symbol an independent probability

```text
(1 − α) / 26 + α × p(English letter),     0 ≤ α ≤ 1,
```

with one unknown fixed bijection from cipher glyphs to English letters. This is
an exploratory model, not an assertion about how the author generated the data.
The fixed English monogram profile is the same one used in
[R25](nachtlorn-book-fullscan.md).

Training is exactly original **page 1**, body rows 1–61 (3,660 letters). The
held-out test is **page 2**, body rows 62–146 (5,076 letters), including the
final I. For each α, sorting training glyph counts and English probabilities in
the same order maximizes the likelihood over all bijections; the concave α
likelihood is then optimized. Ties are broken alphabetically. The resulting
mapping and α are chosen entirely from page 1. The only prediction score is the
page-2 mean log-likelihood ratio against uniform glyphs; no words are read or
selected.

## Result

| Quantity | Result |
|---|---:|
| Page-1 fitted α | 0.112697 |
| Page-1 training LLR, nats/letter | +0.004368 |
| Page-2 held-out LLR, nats/letter | **−0.001674** |
| Positive held-out score and uniform-null tail ≤ 0.01 | **No** |

The page-1 improvement is fitted in sample. On the held-out page the selected
model scores slightly worse than uniform. The fitted α is **not** a recovered
fraction of English, and the fitted letter mapping is not a recovered key.

For context, two fixed Monte Carlo experiments each simulate **10,000** page
pairs and refit the entire page-1 procedure in every replicate. The plus-one
upper-tail rate is the fraction of simulated held-out scores at least as large
as the actual score, with the conventional added-one numerator/denominator:

| Reference model | At least as large / 10,000 | Plus-one rate |
|---|---:|---:|
| Independent uniform glyphs on both pages | 1,619 | 0.161984 |
| Random allocation of the observed pooled counts to the two page sizes | 5,001 | 0.500150 |

The second comparison conditions on the actual total histogram and asks how
unusual the observed split is under random allocation; it does **not** test
whether the totals themselves are uniform. These rates describe the stated
nulls and this fixed procedure, not a global correction for the many historical
puzzle investigations or evidence about the author's RNG. Monte Carlo resolution
is 1/10,001. The predeclared positive-score/0.01 gate is not met.

## Implications and limits

This specific **page-stable, fixed-bijection, independent-letter** mixture does
not provide a useful held-out lead. It does not exclude a sparse localized
message, an actual English component too weak for this screen, changing
alphabets, dependencies, shorter objects, a different reference language, or
other stages. Page membership is used only for this held-out statistical test;
it is not a replacement for the user's separate vertical-strip hypothesis.

The earlier work already recorded the body's near-uniform coincidence and
monogram statistics. R27 is a follow-up with a specified training/held-out
mixture and conditional controls, not a claim that those facts are new. No
candidate fragment, output word, row, zero guide or outlier was chosen.

## Validation

- [Prior registration and outcome](data/nachtlorn-reset-plan.json)
- [Per-page counts, fitted model and calibration](data/nachtlorn-heldout-mixture-results.json)
- [Probe](../scripts/nachtlorn_heldout_mixture.py) and
  [tests](../tests/test_nachtlorn_heldout_mixture.py)

Six tests compare the fitted assignment against permutations and the optimized
mixture against a dense α grid; exercise a planted independent-page synthetic
mixture, tie and zero boundaries, reproducible conditional sampling, input and
overwrite guards, and independently reconstruct the actual fitted scores from
the two page histograms. The synthetic mixture is a control, not a recovered
puzzle message. Sampling uses NumPy 2.2.6 PCG64, seed 20261102; the source run
was executed once. **333 tests across 41 research modules passed** locally with
prior optional research dependencies installed; full-repository Ruff passed.

The original transcript is unchanged: 11,129 bytes, SHA256
`04eddf97e8ebbc9ce2565269508d63c99b60efc7cacf3f2c020f14215dc67e7e`.

```bash
python3 -m pip install --target scratch/nachtlorn-numpy-deps numpy==2.2.6
export PYTHONPATH="$PWD/scratch/nachtlorn-numpy-deps:$PWD"
python3 scripts/nachtlorn_heldout_mixture.py docs/data/nachtlorn-transcript.txt \
  --output scratch/nachtlorn-heldout-mixture-replay.json
python3 -m unittest tests.test_nachtlorn_heldout_mixture -v
```
