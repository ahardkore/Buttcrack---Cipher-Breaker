# buttcrack

**Automatic cipher breaker.** Give it ciphertext and it works out *which* cipher was used, recovers the key, prints the plaintext, and shows you the evidence — including puzzles wrapped in several layers of encoding.

Classical ciphers, CTF-style crypto, encoding chains and XOR. No hints, no key, no idea what you're looking at.

```console
$ buttcrack "Wkh txlfn eurzq ira mxpsv ryhu wkh odcb grj, dqg wkh frpplwwhh gholehudwhg xqwlo plgqljkw."
────────────────────────────────────────────────────────────────────────────────────────────
input      86 characters · IC 0.0447 · entropy 4.41 · A-Z+a-z+punct+space
identified caesar (95%) · also considered: affine
────────────────────────────────────────────────────────────────────────────────────────────

SOLVED  confidence 0.89  in 0.01s

  plaintext
    The quick brown fox jumps over the lazy dog, and the committee deliberated until midnight.

  explanation
    cipher    caesar
    key       3
    method    exhaustive keyspace
    evidence  fitness -4.68 log10/char, words 70%
```

And a three-layer puzzle — base64 around hex around repeating-key XOR — with no hint that any of it is there:

```console
$ buttcrack --file puzzle.txt
────────────────────────────────────────────────────────────────────────────────────────────
input      480 characters · IC 0.1231 · entropy 4.25 · A-Z+a-z+0-9
identified base64 (75%) · also considered: substitution, keyword_substitution
────────────────────────────────────────────────────────────────────────────────────────────

SOLVED  confidence 1.00  in 0.32s

  plaintext
    The council of Venice has decreed that all merchant vessels must pay the new harbour tax
    before entering the lagoon, and the guild of mariners has protested to the doge in writing.

  explanation
    cipher        xor_repeating
    key           LAMP
    decode chain  base64 -> base16 -> xor_repeating
    method        coset IC key length + per-byte chi-squared + quadgram refinement
    evidence      fitness -4.23 log10/char, words 70%
```

---

## 🏛️ Kryptos & Paradigm Kryptos Master Cryptanalytic Suite

This repository houses the complete, publication-grade cryptanalytic research, proofs, and reproducible verification suite for **Jim Sanborn's CIA Kryptos sculpture (K1–K4)** and **Dan Robinson's Paradigm Kryptos suite (PK1–PK10)**:

* 📖 **The Kryptos Decryption Manuscript**: 8 exhaustive chapters covering classical ciphers, polyalphabetic sum-clocks, coordinate geometry, and the 36-year sculpture history. See [`kryptos/THE_KRYPTOS_DECRYPTION_MANUSCRIPT.md`](kryptos/THE_KRYPTOS_DECRYPTION_MANUSCRIPT.md).
* 📑 **Executive Cryptanalytic Brief**: High-density executive summary on final cryptanalytic verdicts and open frontier guidance. See [`kryptos/EXECUTIVE_CRYPTANALYTIC_BRIEF.md`](kryptos/EXECUTIVE_CRYPTANALYTIC_BRIEF.md).
* 🗄️ **Master Solutions Manifest**: Verbatim plaintexts, SHA256 checksums, and mathematical keys for PK1–PK10. See [`kryptos/PARADIGM_KRYPTOS_MASTER_SOLUTIONS.md`](kryptos/PARADIGM_KRYPTOS_MASTER_SOLUTIONS.md) and [`kryptos/pk_submission_manifest.json`](kryptos/pk_submission_manifest.json).
* 🗺️ **Dual-Cipher GPS Sculpture Theorem**: Definitive mathematical proof that PK9 and PK10 padding nulls encode the exact coordinates of Jim Sanborn's CIA Kryptos sculpture ($38^\circ 57' 6'' \text{ N}, 77^\circ 8' 44'' \text{ W}$). See [`kryptos/PARADIGM_KRYPTOS_ARCHITECTURE_MAP.svg`](kryptos/PARADIGM_KRYPTOS_ARCHITECTURE_MAP.svg).
* 🌐 **Interactive Web Application**: Zero-dependency cipher explorer, architecture visualizer, manuscript reader, and live Quagmire III decryptor in [`kryptos-app/`](kryptos-app/). It is published as the `/kryptos/` section of the project's single GitHub Pages site, alongside the browser cipher solver — see [`scripts/build_site.py`](scripts/build_site.py) and [`ventures/README.md`](ventures/README.md).
* ⚡ **1-Second Reproducibility Verification**: Automated test suite executing 11 modules with 100% pass rate:
  ```bash
  python3 kryptos/test_full_suite_reproducibility.py
  ```

---

## Install

Python 3.9 or newer. **Zero runtime dependencies** — the language model ships inside the package and the web interface is `http.server` plus three static files.

```console
$ git clone https://github.com/ahardkore/buttcrack && cd buttcrack
$ python3 -m buttcrack selftest        # verify the install against known answers
```

or install it as a package:

```console
$ pip install .
$ buttcrack "Wkh txlfn eurzq ira"
```

---

## Quick start

```console
# break something (crack is the default command)
buttcrack "Zdvkph uh dg qrrq"
buttcrack --file puzzle.txt --budget 60 --verbose
cat puzzle.txt | buttcrack --json

# what am I looking at, without breaking it?
buttcrack identify --file puzzle.txt

# use it as a cipher, not a cracker
buttcrack encrypt vigenere --key LEMON "meet me at noon"
buttcrack decrypt caesar --key 3 "Zdvkph uh dg qrrq"

# what does it know?
buttcrack ciphers
buttcrack show playfair
buttcrack demo                # encrypt a few messages, then break them with no hints

# web interface
buttcrack serve --port 8080   # then open http://localhost:8080
```

Handy options on `crack`:

| option | what it does |
| --- | --- |
| `--budget SECONDS` | how long the search may run (default 30; big searches want 60–120) |
| `--workers N` | parallel search processes (default: your CPU count) |
| `--file PATH` / stdin | read the ciphertext instead of typing it |
| `--json` | machine-readable report — the same fields the web UI uses |
| `--verbose` | live progress: what is being tried, and what it is scoring |
| `--hint key=VALUE` | a known or suspected key; also `--hint key=hex:ff10` for raw bytes |
| `--language LANG` | plaintext language: `english` (default), `french`, `german`, `italian`, `latin`, `spanish`, or `auto` |
| `--depth N` | how many encoding layers to peel (default 3) |
| `--exhaustive` | keep going after the first confident answer; report every candidate |

---

## What it breaks

36 ciphers, codes and encodings, each with its own attack rather than a brute-force loop over a shared interface.

| family | members | how it is attacked |
| --- | --- | --- |
| **shift** | caesar, rot13, rot47, atbash, affine, reverse | exhaustive keyspace + chi-squared prescreen (26 / 94 / 312 keys) |
| **substitution** | simple substitution, keyword substitution | simulated annealing over 25! alphabets on quadgram fitness |
| **polyalphabetic** | vigenère, beaufort, variant beaufort, gronsfeld, autokey, trithemius | coset index-of-coincidence for the period, then chi-squared per column |
| **transposition** | columnar, rail fence, route, skip/scytale | anagram scoring over key permutations and rail counts |
| **polygraphic** | playfair, bifid | genetic algorithm over 5×5 / 6×6 grids (see *Limits*) |
| **wheel** | M-94 / CSP-488 | hill climb over 25! disk orders, quadgram-scored per read row |
| **xor** | single-byte, repeating-key | byte-coset IC for the key length, per-byte chi-squared, then refinement |
| **codes** | morse, bacon (+ case variant), a1z26, polybius | structural decode — these are recognised, not searched |
| **encodings** | base64, base32, base16, base58, base85, url, binary, decimal ASCII | peeled as layers, in any order, to any depth |

`buttcrack ciphers --verbose` prints the table with keyspaces and search costs; `buttcrack show <name>` explains one cipher, gives a working example and states honestly what the solver can and cannot do with it.

**Layered puzzles.** Every encoding above can wrap any cipher, and any cipher can wrap another. The solver peels a layer, re-identifies what is underneath, and keeps going to `--depth` (`max_depth` in the Python API), reporting the whole chain (`base64 -> base16 -> xor_repeating`) and the key of the cipher that actually hid the message.

---

## How it works

**1. A language model, not a word list.** `buttcrack/data/` holds letter n-gram tables for **six languages** — English (258,337 quadgrams, plus an 80,000-word frequency dictionary distilled from a 25-million-word corpus) and French, German, Italian, Latin and Spanish (n-gram only). Every candidate decryption is scored two ways: n-gram log-probability per character (English ≈ −4.3, random ≈ −7.7) and, for English, the fraction of the text made of real words. That pair — not "does it contain a dictionary word" — is what decides whether an answer is right. Pick the model with `--language`; the report always says which one judged the answer. See [docs/language-model.md](docs/language-model.md).

**2. Identification before search.** `identify()` measures the index of coincidence, entropy, character classes and chi-squared distance from English, then asks the questions in the order that discriminates best: *does one of the 26 shifts restore the English distribution?* → monoalphabetic. *Is the distribution intact but no shift reads it?* → transposition. *Is the index of coincidence flat, and does some period split it into English-like columns?* → Vigenère family. Structural tests (base64 alignment, Morse separators, Playfair's refusal to put the same letter twice in a digraph) run alongside. Each hypothesis is reported with a likelihood **and the reason**, and the solver uses those as priors rather than as orders. See [docs/how-it-works.md](docs/how-it-works.md).

**3. Each cipher gets the attack it deserves.** Caesar is 26 keys. Vigenère is a period search plus 26 chi-squared solves per column. Columnar transposition is an anagram search over key permutations. Simple substitution is simulated annealing with parallel restarts. XOR is coset-IC key-length detection followed by per-byte frequency analysis. Nothing is brute-forced that can be reasoned about.

**4. Confidence is earned, not asserted.** A reported confidence blends language fitness, word coverage and *how much text there was to judge*. A 40-letter solve cannot be as certain as a 400-letter one, so the evidence rule caps short answers (`MIN_LETTERS_PER_COLUMN_TRUST`, and per-cipher column counts: a Playfair grid has 25 cells and wants ~6 letters each before the answer is called solved rather than plausible). When the solver is unsure it says so in the report instead of guessing.

**5. Equivalences are named.** Atbash *is* affine with `a = 25, b = 25`; a Vigenère key of all-`A`s is a Caesar; a digit-only Vigenère key is Gronsfeld. Where two ciphers can produce the same plaintext, the report picks the most specific attribution and says in `notes` that the alternative was considered — so you are not told "affine" when the puzzle author meant "atbash".

---

## Reading the output

* **`SOLVED confidence 0.89`** — the plaintext reads as English, the key is exhaustive or uniquely determined, and there was enough text to judge. Confidence ≥ 0.86 means the solver would bet on it; ≥ 0.62 means it reads correctly but the evidence is thinner.
* **`BEST GUESS`** — a reading that scores well but does not clear the solved bar: the right family, often most of the key. The `caveat` note says what to do: raise `--budget`, add more ciphertext, or pass `--hint`. (`NOT BROKEN` means nothing scored above the noise floor.)
* **`alternatives`** — the next-best readings, with their scores and the first characters of their plaintext. Useful when two keys genuinely fit.
* **`word breaks recovered`** — when the ciphertext had no spaces, the report shows the letters *and* a best-effort respacing from the dictionary.
* **`formatted`** — the plaintext in the layout of the original: case, punctuation and line breaks are restored wherever the cipher preserved positions (Caesar, Vigenère, Atbash, ROT47 do; reverse and the polygraphic ciphers cannot).

Machine-readable everywhere: `--json` on the CLI, `POST /api/crack` (which returns a job id to poll at `/api/job/<id>`) in the web UI, or `buttcrack.solve(text)` in Python.

---

## Python API

```python
from buttcrack import solve, identify, encrypt, decrypt

report = solve("Wkh txlfn eurzq ira mxpsv ryhu wkh odcb grj", budget=10)
report = solve("EPHMAM...", budget=30, language="french")   # judge as French
report = solve_auto("EPHMAM...", budget=30)                 # probe all six, pick the fit
print(report.solved)        # True
print(report.cipher)        # 'caesar'
print(report.key_repr)      # '3'
print(report.plaintext)     # 'The quick brown fox jumps over the lazy dog'
print(report.path)          # 'caesar'
print(report.evidence)      # {'fitness': -4.51, 'words': 0.61, ...}

hypotheses, stats = identify("Zdvkph uh dg qrrq")
print([(h.cipher, h.likelihood) for h in hypotheses[:3]])
# [('caesar', 0.95), ('affine', 0.45)]

encrypt("meet me at noon", "vigenere", "LEMON")   # 'Xiqh zp ef bbzr.'
decrypt("Xiqh zp ef bbzr.", "vigenere", "LEMON")   # 'Meet me at noon.'
```

`report.candidates` holds every reading the search produced, ranked; each one carries its own plaintext, key, confidence and the notes explaining how it was found.

---

## Web interface

`buttcrack serve` starts a local server (stdlib `http.server`, no framework, no build step) with three panels:

* **Break** — paste ciphertext, watch the identification hypotheses arrive, then the ranked readings with confidence, key, decode chain and evidence. Long searches run as background jobs and poll. The language dropdown sends `--language` (including *Auto-detect*).
* **Playground** — pick any of the 36 ciphers, type a key, encrypt or decrypt, and see the layout preserved.
* **Reference** — the cipher table with keyspaces, search costs and each cipher's own notes on what breaks it.

Bind it to the network with `--host 0.0.0.0`; it serves only the API and its own three static files, refuses path traversal, and holds no state beyond the in-memory job list.

There is also a browser-only quick version — a compact trigram solver that runs entirely client-side, no server and no upload — published with a field guide to the classical ciphers at **[ahardkore.github.io/Buttcrack---Cipher-Breaker](https://ahardkore.github.io/Buttcrack---Cipher-Breaker)**. It covers the common puzzle families; everything this README describes (36 ciphers, six languages, the M-94) is the full local tool.

---

## Beyond English

Six plaintext models ship in the box, selected with `--language` (or the `language=` keyword to `solve`, or the dropdown in the web UI):

```console
$ buttcrack ciphertext.txt --language french --budget 30
$ buttcrack ciphertext.txt --language auto          # probe all six, then commit
```

* **Auto mode** spends up to half the budget probing each model on a short solve, then hands the rest to whichever read the most language. Cheap ciphers usually solve outright inside their probe; English is probed first, so the common case costs one short probe.
* **The report names its judge.** `language` says which model produced the verdict. If you crack without naming a language and the plaintext turns out to be French, the report says so (`reads as: french`) and suggests the rerun — because the English model will happily *solve* French text with an English-calibrated confidence and meaningless word respacing.
* **Only English has a dictionary.** The five other models judge on n-gram fitness alone (their thresholds are measured per language and recorded in `model_meta.json`). What that costs in ranking honesty is spelled out under *Limits*.

---

## Limits — read this before you trust an answer

buttcrack is a cryptanalysis tool for **classical and puzzle-grade cryptography**. Being straight about the boundaries:

* **It cannot break modern cryptography.** AES, RSA, ChaCha20, Ed25519 and anything else with a proper key schedule and a real key length are out of reach for *any* tool of this kind — that is a statement about mathematics, not about this code. If your ciphertext came from a real cipher with a real key, no amount of quadgram scoring will help.
* **Playfair and Bifid are partial.** A 5×5 grid has 25! arrangements and one misplaced cell costs ~0.9 log10 per character of fitness — five times what a wrong substitution alphabet costs — so the truth's basin is only a few swaps wide. A pure-Python genetic algorithm recovers roughly nine letters in ten from ~1,500 letters of ciphertext in 90 seconds; whether the last few cells fall into place depends on the seed. The report tells you which case you got. With `--hint key=MONARCHY` both are exact immediately.
* **Short text is weak evidence, and the tool says so.** Below ~50 letters the chi-squared distributions of "English under a shift" and "Vigenère" overlap almost completely (measured: English at n = 35 reaches 1.47 at p99 while Vigenère starts at 0.90). `identify` then reports several plausible families with low likelihoods instead of inventing certainty, and confidence is capped accordingly. The solver still attacks all of them.
* **Some ciphers are lossy by design.** Playfair pads with `X` and splits doubled letters; Bacon merges U/V and I/J; Polybius and Bifid merge I/J. Comparisons in the tests and the selftest fold those away, and the report notes it — you get the letters back, not the typography.
* **Attribution can be equivalent-but-different.** Atbash may be reported as `affine (25, 25)`; a Vigenère with a one-letter key may be reported as `caesar`. The plaintext is right and the `notes` field explains the equivalence.
* **Non-English models have no dictionary.** Only English ships a word list; the other five languages judge on n-gram fitness alone. Two honest consequences, both measured: (1) a slightly wrong reading can outscore the true one — on a 197-letter German Caesar, a substitution near-miss disagreeing on 4 rare letters beat the true shift by 0.05 confidence — so foreign-language reports grade "solved" on fitness, not word-perfectness; (2) the English model *will* solve its sibling languages (French at 0.88 confidence, Italian 0.86) and report inflated confidence — the report's `reads as` note flags this and names the `--language` rerun that fixes it. `--language auto` probes all six models (up to half the budget) and is reliable for cheap ciphers, but for an expensive cipher it can only rank partial readings, so name the language when you know it.
* **The M-94 is a genuine search.** 25! ≈ 1.5×10²⁵ disk orders; the hill climb over pairwise swaps lands from ~200 letters given a real slice of budget (measured: 2-in-3 solves at 250 letters inside 20 s with 2 workers; the true order's read row is always found once the order is). Below 150 letters the honest-evidence rule caps the verdict below *solved* — 25 wheels want ~6 letters each. `--budget 120 --workers 2` and 250+ letters is the reliable recipe; `--hint key=<order>` is exact immediately.

---

## Development

```console
python3 -m unittest discover -s tests -t .                    # 253 tests, stdlib unittest only
BUTTCRACK_SLOW=1 python3 -m unittest discover -s tests -t .   # + the expensive searches
python3 scripts/run_doctests.py                               # the examples in the docstrings
python3 -m buttcrack selftest                                 # known-answer checks end to end
python3 -m buttcrack selftest --slow                          # + substitution, Playfair, Bifid, M-94
python3 examples/generate.py --check                          # solve every sample puzzle
python3 -m buttcrack demo                                     # encrypt, then break with no hints
pip install -e ".[dev]" && ruff check .                       # lint (CI enforces this)
```

`BUTTCRACK_STRICT=1` turns solver warnings into test failures; CI runs the suite
with it set.

Layout:

```
buttcrack/
  lang.py        n-gram + dictionary model, scoring, confidence
  text.py        normalisation, statistics (IC, entropy, chi-squared), layout
  detect.py      identify(): hypotheses with likelihoods and reasons
  search.py      annealing, hill climbing, parallel restarts
  engine.py      the solver: peel layers, attack, rank, present
  results.py     Candidate / CrackReport, equivalences, evidence rules
  selftest.py    known-answer verification of the whole install
  server.py      REST API + static file serving
  cli.py         the command line
  ciphers/       one module per family, 36 ciphers behind one interface
  data/          the language models (see NOTICE for provenance)
  static/        the web interface
scripts/
  build_language_model.py   rebuild the English data/ from PyPI sources
  import_ngram_tables.py    import the five non-English n-gram tables
  calibrate_scoring.py      re-measure the scoring thresholds
examples/                   sixteen sample puzzles, their answers, and a checker
docs/                       how it works, the cipher table, the language model
tests/                      the suite
```

Every threshold in this project was measured, not guessed — `scripts/calibrate_scoring.py` re-runs the measurements (English under a shift vs. Vigenère vs. random, at seven text lengths, 300 samples each) and the numbers it produces are quoted in the comments next to the constants they justify.

---

## Licence

MIT — see [LICENSE](LICENSE).

The bundled English language model is derived from [wordsegment](https://pypi.org/project/wordsegment/) (Apache-2.0, itself derived from Peter Norvig's tables for the Google Web 1T corpus) and [pyspellchecker](https://pypi.org/project/pyspellchecker/) (MIT). The French, German, Italian, Latin and Spanish n-gram tables are the practicalcryptography.com counts published by James Lyons, and the M-94 disk set is the historical public set. Provenance, versions and the build seed are recorded in [NOTICE](NOTICE) and in `buttcrack/data/model_meta.json`.
