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
  counts (rail fence), route patterns and widths (route), coprime skips (skip),
  ordered set partitions (Myszkowski — its key space is the ordered Bell number
  of the width, 4,683 at width 6, so widths up to 6 are enumerated exactly and
  wider ones climb with moves that merge and split groups, because swapping two
  entries can never turn three read groups into four), and permutations paired
  with the starting chunk size (AMSCO).
* **polygraphic** — a genetic algorithm over 5×5 grids (see below); the Hill
  cipher instead exploits linearity. Decryption is row-separable —
  `p[i] = sum_j D[i][j] * c[j]` depends only on row `i` — so each row is scored
  against English monograms on its own and only the best few per position are
  combined into whole matrices. That turns 157,248 invertible 2×2 keys into 676
  row evaluations, and makes 3×3 (about 1.6e12 keys) tractable at all.
* **wheel** — the M-94 attack hill climbs over pairwise spindle-slot swaps.
  A swap re-decodes only the text positions whose index mod 25 hits one of the
  two slots, and each candidate order is scored by its best of 26 read rows
  (rows are prefiltered on a 60-letter prefix, then the top three are scored in
  full — 3x faster than scoring all 26, and the same answer on every order that
  matters). Parallel restarts with an early exit at certainty.
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
`--depth` (default 6, `max_depth` in the Python API). Peeling uses latin-1 rather than UTF-8 so that a
decoded byte ≥ 0x80 survives the round trip as one byte; re-encoding it as UTF-8
would turn it into two and destroy every XOR key alignment underneath. The report
shows the whole chain, outermost first: `base64 -> base16 -> xor_repeating`.

Depth is not free, and three things pay for it:

* **Evidence rises with depth.** Almost any text is *technically* valid base64
  or base85. At the outermost node those readings are worth one look; by depth 3
  a layer needs a likelihood of 0.5 before it is peeled at all. Structural
  decodes score 0.8–0.95 when they are right and the coincidental readings land
  near 0.4, so the ramp separates them by depth 2 — which is why a genuine
  `base32 -> base16 -> base64 -> morse -> ...` chain still goes all the way down
  while a string of Polybius digits no longer sprouts a base64 branch.
* **Budget follows evidence.** A child node gets
  `0.6 + 0.06 * depth + 0.3 * likelihood` of the time remaining, capped at 0.92;
  a layer the identifier is 92% sure of is not handed the same share as one it
  half believes. Attacks within a phase are funded the same way, in proportion
  to likelihood with a floor of 0.15 so nothing is ever vetoed outright.
* **Nodes are capped.** `MAX_NODES = 400` bounds a single solve however the
  branching works out.

**Six layers of ciphers.** The deepest cipher-on-cipher stacks are handled by a
dedicated search that exists because of one algebraic fact: a transposition and
a monoalphabetic substitution **commute**. A transposition moves letters without
reading them; a substitution rewrites letters without moving them. So any stack
of rail fences, skips, reversals, Caesars, Atbashes and ROT13s — in any order,
however deep — equals *one* permutation followed by *one* substitution.

That collapses "every ordering of six ciphers" into two tractable problems:

1. **The substitution, first and for free.** No transposition changes which
   letters are present, so the ciphertext's letter histogram is the plaintext's
   histogram after whatever substitution was applied. Twenty-six rotations and
   Atbash, scored by chi-squared, name it before a single transposition is
   undone; the correction is applied once to the whole text.
2. **The permutation, breadth first.** What remains is a search over composed
   transposition readings, each state costing one n-gram scoring (full
   dictionary scoring is gated behind it, because it is five times the price).
   Measured at ~13,000 states a second: 13 compositions at one step, 182 at
   two, 2,380 at three, 30,927 at four. Breadth first, so the shallowest
   explanation wins, and fingerprinted, because different stacks frequently
   compose to the same permutation.

A gate decides when it runs at all. Chi-squared per letter against English,
best of the rotations, is 0.116 for English and for *any* transposition of it —
rail fence, columnar, Myszkowski, AMSCO, a six-cipher stack — against 1.711 for
Vigenère, 2.214 for Hill and 3.658 for a simple substitution. The separation is
not subtle, so the search never spends budget on a text it could not explain.
It also runs *after* the expensive attacks: Myszkowski and AMSCO pass the gate
too, and their permutations are not reachable by composing rail fences, so going
first would take the budget from the attacks that were going to solve them.

Six stacked *polyalphabetics* are deliberately not searched: nothing commutes
there, every intermediate state is indistinguishable from noise, and no test
exists to prune the tree.

**Unwrapping ciphers, not just encodings.** A transposition or a reflection
usually leaves *another cipher* behind rather than plaintext, so those results
are explored as nodes of their own: `rail_fence -> caesar` and
`reverse -> vigenere` come apart the same way an encoding chain does. Two
details make it work:

* Every reading has to be tried, not ranked. A transposition permutes letters,
  so all of its keys give the same letter statistics and the same chi-squared
  score; when what is underneath is still enciphered, the correct reading is as
  likely to be last in the list as first. So the solver enumerates the readings
  of the small transpositions (reverse, rail fence, skip) and *probes* each with
  a fixed handful of ciphers — no identification, no peeling, no recursion — at
  a cost bounded by the probe list rather than by the branching factor.
* Unwrapping *non-commuting* ciphers (a transposition over a Vigenère, say)
  stops at two steps per chain. Past that the extra freedom explains any text at
  all, which is a property of the search, not of the message. Commuting stacks
  are exempt because the algebra above collapses them rather than guessing, and
  encoding layers are exempt because they are verified rather than guessed:
  base64 either decodes or it does not.

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
* `CHAIN_STEP_BITS = 12` — every *cipher* step in a decode chain is charged as
  key material, because a step is two choices the search made: which cipher
  (about 5.5 bits with forty-six of them) and which key for it. Without this,
  depth quietly becomes dishonest — three cheap ciphers stacked on 35 characters
  of noise will always find something English-shaped, and
  `rail_fence -> reverse -> trithemius` on eighteen letters came back at 0.71
  before the rule existed. Encoding layers are charged nothing: base64 either
  decodes or it does not, which is exactly why a six-layer encoding stack stays
  believable while a three-cipher chain on a short text does not.

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
5. **Check the caveats.** A `BEST GUESS` verdict carries a note saying what was
   missing: too few letters per key column, a plateau in the search, a layer that
   decoded to something unreadable.

And the boundary that no setting moves: this is cryptanalysis of classical and
puzzle-grade cryptography. AES, RSA, ChaCha20 and Ed25519 with proper keys are
not breakable by frequency analysis, and no tool that claims otherwise is telling
the truth.
