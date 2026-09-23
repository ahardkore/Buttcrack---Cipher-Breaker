# The language model

Every decision this tool makes about whether a candidate plaintext "reads as
English" comes from one place: `buttcrack/data/`. It is a statistical model of
English, not a word list, and it ships inside the package so that nothing needs
a network at runtime.

## What is in `data/`

| file | contents | size |
| --- | --- | --- |
| `english_quadgrams.txt.gz` | 258,337 distinct 4-grams over 110,387,612 letter positions | 752 KB |
| `english_trigrams.txt.gz` | 16,935 trigrams from the same corpus | 64 KB |
| `english_bigrams.txt.gz` | all 676 bigrams from the same corpus | 4 KB |
| `english_words.json.gz` | 80,000 most frequent English words with counts | 564 KB |
| `model_meta.json` | build provenance: sources, versions, seed, corpus size, table counts | 4 KB |

`model_meta.json` is the receipt. It records that the model was built from a
25,000,000-word sample (seed 20260923), which upstream packages supplied the
frequency data and under which licences, how long the build took, and how many
entries each table ended up with — so a build is reproducible and the provenance
travels with the data instead of living in a commit message.

The model is loaded lazily: `get_model()` reads the quadgram table on first use
(about 21 s cold on a 2-core sandbox, then cached in the process). Scoring a
candidate is a dictionary lookup per 4-gram, which is why a substitution search
can evaluate hundreds of thousands of alphabets.

## Provenance and licences

The tables are derived from two openly licensed PyPI packages, fetched at build
time by `scripts/build_language_model.py`:

* **wordsegment 1.3.1** (Apache-2.0) — supplies the unigram and bigram frequency
  lists originally compiled by Peter Norvig from the Google Web 1T corpus. The
  build script uses those tables to generate trigram and quadgram counts over a
  25-million-word sample.
* **pyspellchecker 0.9.0** (MIT) — supplies the English word-frequency
  dictionary, from which the 80,000 most common words were taken.

Neither project is a runtime dependency; only their data is used, and only
through the build script. Full attribution is in [NOTICE](../NOTICE).

## How a candidate is scored

`LanguageModel.score(text)` returns an `EnglishScore` with several views, because
no single statistic is trustworthy on its own:

| view | what it is | English | noise |
| --- | --- | --- | --- |
| `fitness` | mean log10 probability per character under the quadgram model | ≈ −4.3 | ≈ −7.7 |
| `words` | fraction of letters that sit inside dictionary words of 4+ letters | ≈ 0.62+ | ≈ 0.05 |
| `segmentation` | Viterbi word-segmentation log10 per character | ≈ −0.8 | ≈ −1.4 |
| `ic` | index of coincidence of the sample | ≈ 0.066 | ≈ 0.038 |
| `chi_squared` | distance per character from the English letter distribution | ≈ 0.1 | ≈ 1.5+ |

`confidence` is the number the engine ranks and thresholds on. It is a weighted
blend of two ramps:

```python
FITNESS_GOOD, FITNESS_BAD = -4.30, -6.20     # fitness -> 1.0 / 0.0
WORDS_GOOD,   WORDS_BAD   =  0.62,  0.20     # word coverage -> 1.0 / 0.0
WEIGHTS = {"fitness": 0.55, "words": 0.45}   # 40+ letters
SHORT_WEIGHTS = {"fitness": 0.35, "words": 0.65}   # under 40 letters
```

Below 40 letters word coverage carries more weight, because quadgram fitness on a
short sample is dominated by which letters happen to be missing; above it,
fitness is the more stable of the two. A text that uses too few distinct letters
is penalised separately (`VARIETY_GOOD, VARIETY_BAD = 0.45, 0.18`), which is what
stops a repeated-letter fake from scoring as prose.

Two thresholds turn confidence into a verdict:

* `SOLVED_CONFIDENCE = 0.62` — the report says SOLVED.
* `CERTAIN_CONFIDENCE = 0.86` — the search stops immediately; there is nothing
  left to gain.

Below `MIN_TRUSTED_LETTERS = 12` nothing is called solved at all, and a fragment
under `FRAGMENT_LETTERS = 8` is capped at `FRAGMENT_CAP = 0.61`: readable, but
not proof. Search inner loops use a cheaper variant (`search_fitness`, first 400
characters, no normalisation) so a hot loop is not paying for punctuation
stripping.

## Calibration: measured, not guessed

Every constant above came from `scripts/calibrate_scoring.py`, which scores
English samples from `examples/english_samples.txt` against deliberate failures —
random letters, wrong Caesar shifts, reversed text, near-miss substitution keys,
transposed text — and prints the percentiles that justify the ramp endpoints.

The identification thresholds in `detect.py` were measured the same way, 300
samples at each of seven lengths:

| letters | English under a shift, p99 chi²/char | Vigenère, p5 chi²/char |
| --- | --- | --- |
| 25 | 1.90 | 1.10 |
| 35 | 1.40 | 1.10 |
| 50 | 1.05 | 1.00 |
| 100 | 0.46 | 0.80 |
| 250 | 0.23 | 0.76 |

That table is the reason the "is this a shift cipher?" threshold is
`0.6 + 25/n` rather than a single number, and the reason the tool refuses to be
confident below about 50 letters: the two distributions genuinely overlap there.
It is also why a pangram is pathological — `the quick brown fox…` at 35 letters
measures chi² ≈ 2.4 because it uses every letter exactly once, which is the
opposite of English's letter distribution. No threshold separates that from a
Vigenère without also producing false positives, so the detector reports a weak
hypothesis and the solver attacks the family anyway.

## Rebuilding and extending

```console
python3 scripts/build_language_model.py --help     # rebuild data/ from PyPI
python3 scripts/calibrate_scoring.py               # re-measure the thresholds
```

The build needs network access to PyPI and about a minute; it rewrites `data/`
and `model_meta.json` deterministically from the recorded seed.

**Another language** means new n-gram tables and a new word list, then a
re-calibration: the ramp endpoints are properties of the corpus, not universal
constants. `LanguageModel(language=..., data_dir=...)` already takes both, and
the file naming convention (`<language>_<order>grams.txt.gz`,
`<language>_words.json.gz`) is the only contract the loader assumes. What does
*not* transfer is the letter-level machinery — `A26`, the IC of English (0.0667),
the chi-squared thresholds and the byte-frequency table used by the XOR attacks
are all English-specific.
