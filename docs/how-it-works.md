# How buttcrack works

The solver is a pipeline of five stages. Each one narrows the space the next one
has to search, and each one records *why* it decided what it decided, so the
final report can show its working instead of just an answer.

```
ciphertext
   │
   ├─ 1. characterise()      length, IC, entropy, charset classes, letter histogram
   │
   ├─ 2. identify()          ranked hypotheses, each with a likelihood and a reason
   │
   ├─ 3. schedule            cost-ordered attack plan, hypotheses used as priors
   │
   ├─ 4. attack + peel       per-cipher cryptanalysis, recursing through encodings
   │
   └─ 5. rank + present      confidence, evidence rules, equivalences, layout
```

Everything below is what the code actually does; the numbers are the constants in
the source, and where a constant was chosen by measurement the measurement is
quoted next to it.

---

## 1. Characterise

`text.characterise()` measures the input before anything guesses at it:

| measurement | what it separates |
| --- | --- |
| index of coincidence | monoalphabetic (≈0.066) from polyalphabetic/polygraphic (≈0.038–0.045) |
| chi-squared per character vs. English letter frequencies | "English distribution, wrong labels" from "distribution destroyed" |
| Shannon entropy | encodings and XOR (high, flat) from letter ciphers (≈4.2–4.5) |
| charset classes | `A-Z+a-z+punct+space` (a message) vs `A-Za-z0-9+/=` (a blob) vs high bytes (a payload) |
| letter variety | prose from a text that only uses a handful of distinct letters |
| best period by coset IC / normalised Hamming distance | the key length of a Vigenère or XOR |

Short samples are treated as short: the chi-squared threshold relaxes as
`0.6 + 25/n`, because at n = 35 even real English under a shift reaches 1.47 at
p99 while a Vigenère text starts at 0.90 — measured over 300 samples at each of
seven lengths (`scripts/calibrate_scoring.py` re-runs the measurement).

## 2. Identify

`detect.identify()` turns those measurements into hypotheses. The questions are
asked in the order that discriminates best, because on a short text the cheap
structural questions are the only ones with an answer:

1. **Is this an encoding?** Morse separators, base64/base58/base32 alphabets and
   alignment, hex, A1Z26 digit groups, Bacon's A/B runs, binary, URL escapes.
   A word-shaped run of short alphabetic tokens (`is_word_shaped`) is *prose*,
   whatever alphabet it happens to fit — that single test is the difference
   between "Caesar ciphertext" and "base64 blob" for `Wkh txlfn eurzq ira`.
2. **Does one of the 26 shifts restore the English distribution?** If yes, this is
   a shift cipher (likelihood 0.95), and if the shift is 13 it is named ROT13
   (0.96). This test is asked before the index-of-coincidence questions because
   it is a direct measurement rather than an inference, and on a short message IC
   is too noisy to trust.
3. **Is the distribution intact but no shift reads it?** Then letters were moved,
   not replaced: columnar (0.85), rail fence (0.70), skip and route (0.60).
4. **Is IC English-like but the distribution permuted?** Monoalphabetic
   substitution (0.90), keyword substitution (0.80), atbash (0.35).
5. **Is IC flat?** Either a period splits it into English-like columns — Vigenère
   (0.85) with Beaufort and Variant Beaufort (0.60) — or nothing does, and the
   honest answer is a weighted list of the polyalphabetic and polygraphic
   families scaled by how much text there is to judge (`min(1, n/120)`).
6. **Below 60 letters, an inconclusive shift test is still reported** (0.20 +
   0.35 × closeness) rather than dropped: "a shift was considered and could not
   be decided" is more useful than silence.
7. **If nothing fired**, each cipher is asked for its own `likelihood()` — a
   structural self-assessment — and the results are reported at half weight,
   labelled as self-assessment.

Two rules keep this honest. A hypothesis produced by *decrypting* something
(a shift that restored English, a base64 that decoded) is reported undamped; a
hypothesis produced by *guessing a family* is damped by half when a strong
structural test already explains the text. And every hypothesis carries its
reason string, which is what `identify` prints and what the report shows.

## 3. Schedule

Attacks are ordered by cost class, not by alphabet:

| class | seconds of a 30 s budget | who is in it |
| --- | --- | --- |
| `CHEAP` (1) | 3 s slice | caesar, rot13, rot47, atbash, affine, reverse, trithemius, all codes and encodings, rail fence, skip |
| `MODERATE` (3) | 6 s slice | vigenère family, autokey, route, xor_repeating |
| `EXPENSIVE` (10) | 25 s slice | substitution, keyword_substitution, columnar, playfair |
| `BRUTAL` (30) | 12 s slice | bifid |

The identification hypotheses are blended into that order as priors
(`_blend_priors`): a cipher the detector named goes first inside its cost class,
but it never jumps the class boundary, so a 26-key Caesar answer still arrives in
milliseconds even when the detector is confused. Cheap attacks run to completion
before expensive ones start, and the search exits early once a candidate reaches
`CERTAIN_CONFIDENCE` (0.86).

## 4. Attack and peel

Each cipher implements its own `crack()`. There is no generic brute-force loop
over a shared keyspace interface — that would be both slower and dumber:

* **shift** — exhaustive, prescreened by chi-squared plus printable-character
  ratio. ROT47 overrides the prescreen with quadgram fitness, because its
  key + 32 twin decrypts the same message with the case flipped and only the
  language model can tell the two apart.
* **substitution** — simulated annealing over mixed alphabets on quadgram
  fitness, with parallel restarts and first-improvement hill climbing to finish.
* **polyalphabetic** — coset IC (and Kasiski-style repeating-segment distances)
  for the period, then chi-squared per column; Gronsfeld restricts columns to
  ten shifts, autokey decomposes the chain.
* **transposition** — anagram scoring over key permutations (columnar), rail
  counts (rail fence), route patterns and widths (route), coprime skips (skip).
* **polygraphic** — a genetic algorithm over 5×5 grids (see below).
* **xor** — byte-coset IC for the key length (floor 1/256, at least 8 bytes per
  coset, top 8 candidates plus their divisors), per-byte chi-squared against an
  English *byte* table, then quadgram refinement and polish of up to 40 bytes per
  key position. Reported keys are reduced to their shortest repeating period, so
  `LAMPLAMPLAMPLAMP` comes back as `LAMP`.
* **codes and encodings** — decoded structurally; they are recognisers, not
  searches.

**Peeling.** Every encoding and code is also a *layer*. After each attack round
the solver asks the layer ciphers whether the current text looks like something
they can strip (`likelihood ≥ STRONG_LAYER = 0.6`), peels it, and recurses — to
`--depth` (default 3, `max_depth` in the Python API). Peeling uses latin-1 rather than UTF-8 so that a
decoded byte ≥ 0x80 survives the round trip as one byte; re-encoding it as UTF-8
would turn it into two and destroy every XOR key alignment underneath. The report
shows the whole chain, outermost first: `base64 -> base16 -> xor_repeating`.

**Playfair, honestly.** A 5×5 grid has 25! arrangements and one misplaced cell
costs about 0.9 log10 per character of fitness — five times what a wrong
substitution alphabet costs — so the truth's basin of attraction is only a few
swaps wide. Measured on 1,600 letters: the true grid scores −4.29, a random grid
−7.73, a first-improvement climb from random converges in 0.4 s to about −6.5
with ~5 usable cells, iterated local search plateaus near −6.2, and simulated
annealing alone plateaus at the same place. Crossover is what breaks the
plateau: local optima are wrong about *different* cells, so a population of 12
with uniform crossover, mutation and tail reseeding reaches about −5.4 in 45 s —
nine letters in ten, sometimes enough to cross the solve threshold, sometimes
not. The scoring window grows with the answer (400 characters while the
population is noise, the whole text past −5.6) and a quarter of each worker's
slice is held back for a best-improvement polish. Bifid is weaker still and is
labelled experimental in the cipher table.

**Parallelism.** Searches with restarts (substitution, playfair, bifid, XOR
polish) fan out across `--workers` processes with different seeds; each worker
gets a slice of the remaining budget and its own deadline, and the parent ranks
whatever comes back. Everything else is single-process, because a 26-key sweep
does not deserve a process pool.

## 5. Rank and present

Candidates are ranked by `Candidate.sort_key`: confidence, then fitness, then
fewer decode steps, then a shorter key, then an equivalence rank that prefers the
name a human would use. That last part matters because several ciphers can
produce the same plaintext:

* Atbash **is** affine with `a = 25, b = 25` — a short text may be reported as
  either, and the notes say so.
* Variant Beaufort with key K decrypts exactly what Vigenère decrypts with key
  −K; Gronsfeld is Vigenère restricted to digits. `EQUIVALENT_CIPHER_RANK`
  (`vigenere` < `beaufort` < `variant_beaufort` < `gronsfeld`) breaks the tie
  toward the name people recognise, and only ever on ties.
* A shift of 13 is reported as ROT13 rather than Caesar 13.

**Confidence is earned.** It blends n-gram fitness and dictionary word coverage
(weights 0.55/0.45, or 0.35/0.65 below 40 letters where word coverage is the
more stable signal), then applies evidence rules:

* `MIN_TRUSTED_LETTERS = 12` — below that, nothing is called solved.
* `FRAGMENT_LETTERS = 8`, `FRAGMENT_CAP = 0.61` — a fragment can be readable and
  still not be proof.
* `MIN_LETTERS_PER_COLUMN_TRUST = 6` with a per-cipher column count — a Vigenère
  with a 12-letter key wants 72 letters, a Playfair grid (25 cells) wants 150,
  Bifid (36) wants 216. Fewer than that and the confidence is capped at
  `EVIDENCE_CAP = 0.61`, i.e. "reads correctly, evidence thin".

**Layout.** Where the cipher maps letter *i* to letter *i* (shift, substitution,
polyalphabetic, polygraphic families) and nothing was peeled underneath, the
original case, punctuation and line breaks are laid back over the recovered
letters. ROT47 and reverse are excluded — ROT47 works on bytes and reverse
reorders, so neither has a layout to preserve. When the layout cannot be
preserved (a transposition, or text that arrived without spaces) the report
includes a dictionary-segmented respacing instead, and says which of the two it
did.

---

## When it does not solve

In rough order of usefulness:

1. **Give it more text.** Every threshold in the project exists because short
   samples are ambiguous. 300 letters changes what is provable.
2. **Give it more time.** `--budget 120` and `--workers 4` matter most for
   substitution, columnar, playfair and bifid.
3. **Give it a hint.** `--hint key=LEMON`, `--hint key=hex:ff10`, or a crib in
   the API. A hinted solve is exact and immediate for every cipher here.
4. **Read the alternatives.** When two keys fit, the report lists both with their
   scores and the first characters of each plaintext — often the second one is
   the answer and the first is an equivalent attribution.
5. **Check the caveats.** A `PARTIAL` verdict carries a note saying what was
   missing: too few letters per key column, a plateau in the search, a layer that
   decoded to something unreadable.

And the boundary that no setting moves: this is cryptanalysis of classical and
puzzle-grade cryptography. AES, RSA, ChaCha20 and Ed25519 with proper keys are
not breakable by frequency analysis, and no tool that claims otherwise is telling
the truth.
