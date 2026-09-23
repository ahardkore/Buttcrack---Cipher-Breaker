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
| `--depth N` | how many encoding layers to peel (default 3) |
| `--exhaustive` | keep going after the first confident answer; report every candidate |

---

## What it breaks

35 ciphers, codes and encodings, each with its own attack rather than a brute-force loop over a shared interface.

| family | members | how it is attacked |
| --- | --- | --- |
| **shift** | caesar, rot13, rot47, atbash, affine, reverse | exhaustive keyspace + chi-squared prescreen (26 / 94 / 312 keys) |
| **substitution** | simple substitution, keyword substitution | simulated annealing over 25! alphabets on quadgram fitness |
| **polyalphabetic** | vigenère, beaufort, variant beaufort, gronsfeld, autokey, trithemius | coset index-of-coincidence for the period, then chi-squared per column |
| **transposition** | columnar, rail fence, route, skip/scytale | anagram scoring over key permutations and rail counts |
| **polygraphic** | playfair, bifid | genetic algorithm over 5×5 / 6×6 grids (see *Limits*) |
| **xor** | single-byte, repeating-key | byte-coset IC for the key length, per-byte chi-squared, then refinement |
| **codes** | morse, bacon (+ case variant), a1z26, polybius | structural decode — these are recognised, not searched |
| **encodings** | base64, base32, base16, base58, base85, url, binary, decimal ASCII | peeled as layers, in any order, to any depth |

`buttcrack ciphers --verbose` prints the table with keyspaces and search costs; `buttcrack show <name>` explains one cipher, gives a working example and states honestly what the solver can and cannot do with it.

**Layered puzzles.** Every encoding above can wrap any cipher, and any cipher can wrap another. The solver peels a layer, re-identifies what is underneath, and keeps going to `--depth` (`max_depth` in the Python API), reporting the whole chain (`base64 -> base16 -> xor_repeating`) and the key of the cipher that actually hid the message.

---

## How it works

**1. A language model, not a word list.** `buttcrack/data/` holds letter n-gram tables (258,337 quadgrams) and an 80,000-word frequency dictionary, distilled from a 25-million-word English corpus. Every candidate decryption is scored two ways: n-gram log-probability per character (English ≈ −4.3, random ≈ −7.7) and the fraction of the text made of real words. That pair — not "does it contain a dictionary word" — is what decides whether an answer is right. See [docs/language-model.md](docs/language-model.md).

**2. Identification before search.** `identify()` measures the index of coincidence, entropy, character classes and chi-squared distance from English, then asks the questions in the order that discriminates best: *does one of the 26 shifts restore the English distribution?* → monoalphabetic. *Is the distribution intact but no shift reads it?* → transposition. *Is the index of coincidence flat, and does some period split it into English-like columns?* → Vigenère family. Structural tests (base64 alignment, Morse separators, Playfair's refusal to put the same letter twice in a digraph) run alongside. Each hypothesis is reported with a likelihood **and the reason**, and the solver uses those as priors rather than as orders. See [docs/how-it-works.md](docs/how-it-works.md).

**3. Each cipher gets the attack it deserves.** Caesar is 26 keys. Vigenère is a period search plus 26 chi-squared solves per column. Columnar transposition is an anagram search over key permutations. Simple substitution is simulated annealing with parallel restarts. XOR is coset-IC key-length detection followed by per-byte frequency analysis. Nothing is brute-forced that can be reasoned about.

**4. Confidence is earned, not asserted.** A reported confidence blends language fitness, word coverage and *how much text there was to judge*. A 40-letter solve cannot be as certain as a 400-letter one, so the evidence rule caps short answers (`MIN_LETTERS_PER_COLUMN_TRUST`, and per-cipher column counts: a Playfair grid has 25 cells and wants ~6 letters each before the answer is called solved rather than plausible). When the solver is unsure it says so in the report instead of guessing.

**5. Equivalences are named.** Atbash *is* affine with `a = 25, b = 25`; a Vigenère key of all-`A`s is a Caesar; a digit-only Vigenère key is Gronsfeld. Where two ciphers can produce the same plaintext, the report picks the most specific attribution and says in `notes` that the alternative was considered — so you are not told "affine" when the puzzle author meant "atbash".

---

## Reading the output

* **`SOLVED confidence 0.89`** — the plaintext reads as English, the key is exhaustive or uniquely determined, and there was enough text to judge. Confidence ≥ 0.86 means the solver would bet on it; ≥ 0.62 means it reads correctly but the evidence is thinner.
* **`PARTIAL`** — the right family, most of the key, not all of it. The `caveat` note says what to do: raise `--budget`, add more ciphertext, or pass `--hint`.
* **`alternatives`** — the next-best readings, with their scores and the first characters of their plaintext. Useful when two keys genuinely fit.
* **`word breaks recovered`** — when the ciphertext had no spaces, the report shows the letters *and* a best-effort respacing from the dictionary.
* **`formatted`** — the plaintext in the layout of the original: case, punctuation and line breaks are restored wherever the cipher preserved positions (Caesar, Vigenère, Atbash, ROT47 do; reverse and the polygraphic ciphers cannot).

Machine-readable everywhere: `--json` on the CLI, `POST /api/crack` (which returns a job id to poll at `/api/job/<id>`) in the web UI, or `buttcrack.solve(text)` in Python.

---

## Python API

```python
from buttcrack import solve, identify, encrypt, decrypt

report = solve("Wkh txlfn eurzq ira mxpsv ryhu wkh odcb grj", budget=10)
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

* **Break** — paste ciphertext, watch the identification hypotheses arrive, then the ranked readings with confidence, key, decode chain and evidence. Long searches run as background jobs and poll.
* **Playground** — pick any of the 35 ciphers, type a key, encrypt or decrypt, and see the layout preserved.
* **Reference** — the cipher table with keyspaces, search costs and each cipher's own notes on what breaks it.

Bind it to the network with `--host 0.0.0.0`; it serves only the API and its own three static files, refuses path traversal, and holds no state beyond the in-memory job list.

---

## Limits — read this before you trust an answer

buttcrack is a cryptanalysis tool for **classical and puzzle-grade cryptography**. Being straight about the boundaries:

* **It cannot break modern cryptography.** AES, RSA, ChaCha20, Ed25519 and anything else with a proper key schedule and a real key length are out of reach for *any* tool of this kind — that is a statement about mathematics, not about this code. If your ciphertext came from a real cipher with a real key, no amount of quadgram scoring will help.
* **Playfair and Bifid are partial.** A 5×5 grid has 25! arrangements and one misplaced cell costs ~0.9 log10 per character of fitness — five times what a wrong substitution alphabet costs — so the truth's basin is only a few swaps wide. A pure-Python genetic algorithm recovers roughly nine letters in ten from ~1,500 letters of ciphertext in 90 seconds; whether the last few cells fall into place depends on the seed. The report tells you which case you got. With `--hint key=MONARCHY` both are exact immediately.
* **Short text is weak evidence, and the tool says so.** Below ~50 letters the chi-squared distributions of "English under a shift" and "Vigenère" overlap almost completely (measured: English at n = 35 reaches 1.47 at p99 while Vigenère starts at 0.90). `identify` then reports several plausible families with low likelihoods instead of inventing certainty, and confidence is capped accordingly. The solver still attacks all of them.
* **Some ciphers are lossy by design.** Playfair pads with `X` and splits doubled letters; Bacon merges U/V and I/J; Polybius and Bifid merge I/J. Comparisons in the tests and the selftest fold those away, and the report notes it — you get the letters back, not the typography.
* **Attribution can be equivalent-but-different.** Atbash may be reported as `affine (25, 25)`; a Vigenère with a one-letter key may be reported as `caesar`. The plaintext is right and the `notes` field explains the equivalence.
* **The language model is English.** Other languages need their own n-gram tables; `scripts/build_language_model.py` shows how the shipped ones were made.

---

## Development

```console
python3 -m unittest discover -s tests -t .                    # 197 tests, stdlib unittest only
BUTTCRACK_SLOW=1 python3 -m unittest discover -s tests -t .   # + the expensive searches
python3 scripts/run_doctests.py                               # the examples in the docstrings
python3 -m buttcrack selftest                                 # known-answer checks end to end
python3 -m buttcrack selftest --slow                          # + substitution, Playfair, Bifid
python3 examples/generate.py --check                          # solve every sample puzzle
python3 -m buttcrack demo                                     # encrypt, then break with no hints
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
  ciphers/       one module per family, 35 ciphers behind one interface
  data/          the language model (see NOTICE for provenance)
  static/        the web interface
scripts/
  build_language_model.py   rebuild data/ from PyPI sources
  calibrate_scoring.py      re-measure the scoring thresholds
examples/                   fifteen sample puzzles, their answers, and a checker
docs/                       how it works, the cipher table, the language model
tests/                      the suite
```

Every threshold in this project was measured, not guessed — `scripts/calibrate_scoring.py` re-runs the measurements (English under a shift vs. Vigenère vs. random, at seven text lengths, 300 samples each) and the numbers it produces are quoted in the comments next to the constants they justify.

---

## Licence

MIT — see [LICENSE](LICENSE).

The bundled language model is derived from [wordsegment](https://pypi.org/project/wordsegment/) (Apache-2.0, itself derived from Peter Norvig's tables for the Google Web 1T corpus) and [pyspellchecker](https://pypi.org/project/pyspellchecker/) (MIT). Provenance, versions and the build seed are recorded in [NOTICE](NOTICE) and in `buttcrack/data/model_meta.json`.
