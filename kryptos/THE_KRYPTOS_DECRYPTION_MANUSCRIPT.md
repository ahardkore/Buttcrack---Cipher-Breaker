# The Kryptos Decryption Manuscript

### What it takes to break a cipher, what we broke, and how we know

**Edition:** September 2026
**Repository:** `ahardkore/Buttcrack---Cipher-Breaker`
**Reproduce every number in this book:** `python3 scripts/kryptos_ctf.py`, `python3 scripts/build_kryptos_app_data.py`, `python3 -m unittest discover -s tests -t .`

---

## A note on claims, before anything else

Cryptanalysis attracts a particular kind of self-deception. You run a search, it
returns the best thing it found, and the best thing it found always looks a
little like English — because you asked a machine to maximise a measure of
looking-like-English, and it obliged. The discipline is not in the searching. It
is in deciding whether the answer is real.

So this book uses three labels and never blurs them.

| Label | Meaning |
| --- | --- |
| **Verified** | Re-derived here, from the ciphertext, by code you can run. |
| **Published** | Someone else's answer, reproduced here, *not* independently re-derived. |
| **Open** | Unsolved. No claim. |

An earlier edition of this manuscript claimed solutions to PK9 and PK10.
Those claims were wrong, they are retracted in Chapter 9, and the retraction
is included rather than quietly deleted, because how a wrong answer got
believed is more instructive than the correct answer would have been.

---

## Table of contents

**Part I — The sculpture**
1. Langley, 1990
2. K1 and K2: the keyed alphabet
3. K3: the anagram that proves itself
4. K4: ninety-seven characters

**Part II — The instruments**
5. What actually breaks a cipher
6. The measurements: IC, chi-squared, n-grams
7. When search fails and algebra works

**Part III — Paradigm Kryptos**
8. The narrative arc, PK1 to PK7
9. PK8, PK9, PK10: the open frontier — and a retraction

**Part IV — Apparatus**
10. Reproducibility
11. What would move this forward

---

# Part I — The sculpture

## Chapter 1: Langley, 1990

In November 1990 a curved copper screen was dedicated in a courtyard at CIA
headquarters. Jim Sanborn made it; Edward Scheidt, recently retired from the
Agency's Office of Communications, taught him the cryptography. Into the copper
were punched some 1,800 characters in four passages, now called K1 through K4.

Three fell within a decade. The fourth, ninety-seven characters, has not fallen
in public in thirty-six years.

What makes Kryptos unusual is not difficulty. K1 is a polyalphabetic cipher of a
type broken in the nineteenth century, and any laptop reads it instantly. What
makes it unusual is that it was built to be *eventually* readable, in stages, by
someone patient — and that the artist made a mistake in the copper which took
sixteen years to surface. Both facts matter to anyone attacking the fourth
panel, and both are examined here.

---

## Chapter 2: K1 and K2 — the keyed alphabet

### The mechanism

K1 and K2 are Vigenère ciphers with a twist that defeats a naive solver: the
arithmetic happens in a *keyed* alphabet, not in A–Z. The alphabet is the
keyword KRYPTOS followed by the unused letters in order:

```
K R Y P T O S A B C D E F G H I J L M N Q U V W X Z
```

Encryption is ordinary Vigenère addition, but on positions in *that* sequence:

```
index_K(C) = ( index_K(P) + index_K(key letter) ) mod 26
```

This is the cipher the American Cryptogram Association calls Quagmire III, and
it is the single most important thing to understand about Kryptos. A solver that
assumes A = 0 recovers nothing at all — not a degraded answer, *nothing* —
because the per-column shift it finds is a shift of the wrong alphabet. The
statistics look identical; only the labels are wrong. Many people have wasted
weeks on this.

### K1, verified

**Ciphertext (63 characters):**

```
EMUFPHZLRFAXYUSDJKZLDKRNSHGNFIVJYQTQUXQBQVYUVLLTREVJYQTMKYRDMFD
```

**Key:** `PALIMPSEST`. **Result:**

```
BETWEEN SUBTLE SHADING AND THE ABSENCE OF LIGHT
LIES THE NUANCE OF IQLUSION
```

`IQLUSION` is not a transcription error. Sanborn misspelled *illusion*
deliberately, and there are further deliberate misspellings later. In a puzzle
where cribs matter, an artist who plants wrong letters on purpose is telling you
something about how much your assumptions are worth.

**Status: verified.** `buttcrack`'s `quagmire3` reproduces this panel exactly
from ciphertext and key. The same implementation, given no key at all,
recovers the Paradigm Kryptos PK1 keyword from ciphertext alone in about
fifteen seconds (Chapter 8).

### K2, verified — and the missing letter

**Key:** `ABSCISSA`. The plaintext runs to a set of coordinates:

```
IT WAS TOTALLY INVISIBLE   HOWS THAT POSSIBLE
THEY USED THE EARTHS MAGNETIC FIELD X
...
THIRTY EIGHT DEGREES FIFTY SEVEN MINUTES SIX POINT FIVE SECONDS NORTH
SEVENTY SEVEN DEGREES EIGHT MINUTES FORTY FOUR SECONDS WEST
```

— coordinates that land close to the sculpture itself — and ends with a
question about who knows the exact location: *only WW*. William Webster was
Director of Central Intelligence at the dedication, and was handed a sealed
envelope containing the solution.

Now the interesting part. Decrypt the 369 characters that are actually on the
sculpture and the ending reads:

```
... SECONDS WEST   ID BY ROWS
```

The intended text is:

```
... SECONDS WEST   X LAYER TWO
```

Sanborn omitted a letter while cutting the copper. He confirmed it in 2006. The
divergence begins at character 361 of the decryption, and the build script for
this project's Kryptos explorer verifies precisely that: characters 0–360 match
the published plaintext, then the panel and the intention part company.

**Status: verified to character 361, with a documented physical error after it.**
This is worth dwelling on. A cipher is a mathematical object; a sculpture is a
manufactured one. The error is not in the mathematics, and no amount of
cryptanalysis would have revealed it — only the artist could. K4 is on the same
copper, cut by the same hands.

---

## Chapter 3: K3 — the anagram that proves itself

K3 is a transposition: the plaintext letters, reordered. Its solution is a close
paraphrase of Howard Carter's account of breaching Tutankhamun's tomb in
November 1922, ending:

```
... SLOWLY, DESPARATLY SLOWLY ...
CAN YOU SEE ANYTHING Q
```

(`DESPARATLY` is another deliberate misspelling.)

Transposition ciphers have a property that makes verification trivial and
absolute: **they do not change which letters are present, only where they are.**
So the ciphertext must be an exact anagram of the plaintext — same letters, same
counts, different order. That check needs no key, no column order, and no
assumption about the method. The data build for the explorer performs exactly
this test on K3 and on PK2, and refuses to publish an entry that fails it.

It is a small thing, but it is the model for everything in Part II: find the
property the cipher *cannot* violate, and test that, instead of testing whether
the output looks nice.

---

## Chapter 4: K4 — ninety-seven characters

```
OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJKLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR
```

Sanborn has released cribs over the years — plaintext known to sit at known
positions:

| Positions | Plaintext |
| --- | --- |
| 22–25 | `EAST` |
| 26–34 | `NORTHEAST` |
| 64–69 | `BERLIN` |
| 70–74 | `CLOCK` |

Four cribs, thirty-four letters between them, and K4 has still not yielded. That
should calibrate expectations about crib-driven attacks generally: a crib is
decisive *when the cipher is linear in its key* (Chapter 7), and close to
useless when it is not.

Ninety-seven characters is the other problem. At that length many keys produce
readable English, and no statistic distinguishes them — a point developed in
Chapter 6 and demonstrated concretely in Chapter 9.

**Status: open.** This book makes no claim about K4, and readers should treat
any claim about K4 — including confident ones, including ones with impressive
mathematics attached — as requiring the kind of verification set out in
Chapter 10.

---

# Part II — The instruments

## Chapter 5: What actually breaks a cipher

Four ideas, in the order they were discovered, still do most of the work.

**Frequency analysis** (al-Kindi, ninth-century Baghdad). Letters are not
equally common, and a substitution cipher renames them without changing how
often each occurs. Al-Kindi's manuscript on deciphering messages is the first
written description of the method, and it made every monoalphabetic cipher
breakable a thousand years before anyone built a machine.

**The Kasiski examination** (Babbage, 1854, unpublished; Kasiski, 1863).
Repeated fragments in a polyalphabetic ciphertext are usually the same plaintext
encrypted by the same part of a repeating key. Measure the gaps, take their
common factors, and the key length falls out. Babbage broke Vigenère first and
published nothing, possibly at the request of British intelligence during the
Crimean War.

**The index of coincidence** (William Friedman, 1922). The probability that two
letters drawn from a text are the same: about 0.067 for English, 0.038 for
uniform random. Slice a polyalphabetic ciphertext by the right period and each
slice jumps back to English levels. Friedman turned codebreaking into statistics
and coined the word *cryptanalysis*.

**Hill climbing on n-gram fitness** (modern). Score a candidate decryption by
how probable its four-letter sequences are in English; change the key a little;
keep the change if the score improves. English averages about −4.3 per character
under this measure and random text about −7.7. This is what lets a laptop search
25! alphabets. It is not a cleverer idea than anagramming by hand — only a
faster one.

Every attack in this project is one of these four, or a combination.

---

## Chapter 6: The measurements

### What the index of coincidence tells you, and what it does not

| Text | IC |
| --- | --- |
| English prose | ≈ 0.067 |
| Monoalphabetic substitution of English | ≈ 0.067 (unchanged) |
| Any transposition of English | ≈ 0.067 (unchanged) |
| Vigenère, short key | 0.045 – 0.055 |
| Uniform random | ≈ 0.038 |

The first three lines are the important ones. A substitution renames letters and
a transposition moves them; neither changes how often coincidences happen. So IC
separates *polyalphabetic from not*, and tells you nothing whatsoever about
whether you are looking at a substitution or a transposition. For that you need
n-grams: a transposition destroys them while keeping the letter distribution
intact, which is the "good IC, terrible n-grams" fingerprint.

### The evidence rule

Here is the measurement that matters most and gets used least. A recovered key
is only believable if the plaintext is long enough to have pinned it down.

A 26-letter substitution alphabet holds about 88 bits. English carries roughly
3.2 bits of redundancy per letter. So around 28 letters of correct plaintext is
the theoretical minimum before the key is even determined, and in practice you
want several times that. Below it, *many* keys produce readable output and the
search returns whichever one it happened to find.

This project enforces the rule in code. Confidence is capped when the key is
large relative to the recovered text, and — added after the failure described in
Chapter 9 — every cipher step in a decode chain is charged as additional key
material, because each step is a choice the search made.

Without that rule, three cheap ciphers stacked on thirty-five characters of
noise returned "solved" at 0.71 confidence. The text was nonsense. The score was
real. That is the whole problem in one sentence.

---

## Chapter 7: When search fails and algebra works

The most useful discovery in this project's work on the Paradigm Kryptos suite
is about the *shape* of a problem rather than any particular cipher.

### A search that cannot work

Consider a keystream built by adding several short wheels:

```
K[t] = q4[t mod 4] + q5[t mod 5] + q6[t mod 6] + q7[t mod 7]   (mod 26)
```

Four wheels of periods 4, 5, 6 and 7 give a combined period of
lcm = 420 — longer than a 153-character message. No two positions share a key
symbol. Column-wise frequency analysis has nothing to work with: the classical
attack does not merely struggle, it *does not apply*.

Hill climbing seems like the obvious fallback. It does not work either, and the
reason is structural rather than a matter of compute. Every position's key is a
**sum of four unknowns**, so a position decrypts correctly only when all four of
its wheel slots are simultaneously right. Changing one slot earns no partial
credit. The landscape has almost no gradient.

Measured, on synthetic instances of exactly this shape with the answer known:

| Attack | Result |
| --- | --- |
| Simulated annealing, 60 s per instance | **0 of 6 recovered** |
| — and it plateaus at −6.09 fitness | (true key scores −4.25) |
| Longer runs (44k, 176k steps) | no improvement; same plateau |

### An algebra that does

The same structure that defeats search makes the cipher fragile in a different
way: **the keystream is linear in the wheels.** Every known plaintext letter
gives one linear equation

```
q4[t mod 4] + q5[t mod 5] + q6[t mod 6] + q7[t mod 7] = C[t] − P[t]
```

in the 22 unknown wheel values. Of those 22, three are gauge — adding one to
every entry of one wheel and subtracting one from another leaves the keystream
unchanged — so 19 are real. Nineteen known letters therefore determine the key
outright, with no search at all.

| Attack | Result |
| --- | --- |
| Crib of 19 letters, pure linear algebra | **5 of 5 recovered, 0.1 s each** |
| Crib of 16 letters, algebra + annealing in the remainder | 4 of 4, 25 s |
| Crib of 14 letters | 2 of 4 |
| Crib of 12 letters | 0 of 4 |

The boundary sits exactly where the equations begin to outnumber the unknowns,
which is what the algebra predicts. Solving over Z/26 needs one wrinkle: it is
not a field, so the system is solved modulo 2 and modulo 13 and recombined by
the Chinese remainder theorem.

### Two wheels are not like four

If there are only *two* wheels, the problem collapses completely. Fix the short
wheel and what remains is a plain Vigenère of known period, which chi-squared
solves one column at a time. So the entire key space is an enumeration of the
short wheel alone — 456,976 possibilities for a four-letter wheel, each costing
a handful of table lookups. This is exact, not heuristic: if the cipher is a
two-wheel clock of that shape, the key *is* found.

That is how PK3 falls in about five seconds, recovering not merely a working key
but the actual keywords the author used (Chapter 8).

### An operator that annihilates the key

One more tool, because it is the sharpest. A sum of wheels with periods 4, 5, 6
and 7 is killed by a four-tap linear operator:

```
L[s](t) = s[t+67] − s[t+60] − s[t+7] + s[t]  ≡  0   (mod 26)
```

The reasoning: 60 = lcm(4, 5, 6) cancels three wheels, leaving a remainder with
period 7, which a further lag-7 difference cancels. Since `C = P + K` and
`L(K) = 0`, it follows that

```
L(P) = L(C)
```

— a condition on the **plaintext**, computable from the ciphertext alone, with
no key and no search. It cannot find a plaintext. It can *test* one in four
operations, which means an entire book can be checked for a suspected passage at
about 3.4 million letters per second.

One limit, because the obvious guess about it is wrong. Each constraint reads
four plaintext positions spanning 67 characters, so a quoted stretch of `L`
letters yields `L − 67` usable constraints, not `L`. Measured against planted
quotations: 74 letters gives 7 constraints and is undetectable; 90 gives 23 and
is found; 110 gives 43 and is unmistakable. The method finds contiguous
quotations of roughly eighty-five letters and up. Shorter ones are not merely
hard — they are invisible, because the information is not there.

---

# Part III — Paradigm Kryptos

## Chapter 8: The narrative arc, PK1 to PK7

In 2024–26 Dan Robinson published ten challenges — Paradigm Kryptos — built on
the sculpture's machinery: the Kryptos alphabet, Quagmire III, columnar
transposition, matrix ciphers, additive clocks. Unlike most puzzle suites, the
ten plaintexts form one continuous first-person story: an apprentice archivist
hunting the "needle of Pellegrin", fine enough to read any knot, and through it
the lost archive of Francisque Pellegrin.

| # | Cipher | Key | Status here | Solver time |
| --- | --- | --- | --- | --- |
| PK1 | Quagmire III, Kryptos alphabet, period 10 | `PROVENANCE` | **Verified** | ~15 s |
| PK2 | Complete columnar, 50 × 7 | `MARGINS` | **Verified** (anagram) | ~19 s |
| PK3 | Sum-clock, wheels 10 and 8 | `PENTIMENTO` + `ORDINATE` | **Verified** | ~5 s |
| PK4 | Columnar 28 × 8 + dual clock (5, 9) | prose only | Published | — |
| PK5 | Columnar 17 × 16 + Quagmire III | prose only | Published | — |
| PK6 | Double columnar + Quagmire III p6 | `PORTAL` | Published | — |
| PK7 | Quagmire III p6 + 3 × 3 Hill matrix | prose only | Published | — |

"Solver time" means: given the ciphertext and nothing else, how long
`buttcrack` takes to produce the published plaintext. PK1, PK2 and PK3 are
reproduced from scratch. PK4 through PK7 are not, for two distinct reasons
worth separating:

* They are **composites** — a transposition wrapped around a substitution. The
  transposition's key cannot be scored while the text underneath is still
  enciphered, because every column order produces the same letter statistics.
  This is a genuine open problem in the solver, not an implementation gap.
* Their **full keys are not recorded** anywhere in this repository — only
  described in prose ("Dual-Clock Substitution p5 + p9, Transposition Width 8").
  So nothing here can even verify them mechanically. They are marked *published*
  rather than *verified*, and the Kryptos explorer says so on the page.

### PK3 in detail, because it is the satisfying one

PK3's keystream is two wheels of periods 10 and 8 summed over the Kryptos
alphabet, giving a combined period of 40 on a 280-letter message — seven letters
per column, which is too thin for column-wise analysis to be reliable.

The two-wheel collapse of Chapter 7 solves it anyway. Enumerate the eight-letter
wheel over a word list (51,627 candidates), derive the ten-letter wheel by
chi-squared for each, score the result. Elapsed: **3.7 seconds**, and the
recovered wheels are not merely equivalent to the author's — they *are* the
author's:

```
ORDINATE  +  PENTIMENTO
```

That the wheels are English words is not incidental. The author's public hint
about the unsolved PK8 was that its key "has quite a lot of entropy, but some
structure". PK3 shows what structure means here.

---

## Chapter 9: PK8, PK9, PK10 — the open frontier, and a retraction

### The retraction

The previous edition of this manuscript contained chapters titled "Cracking PK9"
and "Cracking PK10". They presented recovered plaintext. Here is what it
offered as the solution to PK9:

> LARD A DEFUNCT ORD. Q. BOOM R BETH SKWJER EAST Y MARIN PRAY I ALMS O I SEAR
> VE MY LAIL E BOTH HEED THE DAMES QUENCH LAY IM IRLO FAT SEARED CIS AND ID BY
> US CHES ALSO MY RELIEF ORES SESTIA

This is not English. It is the output of a search that maximised a score, and
the manuscript defended it by explaining each failure as an archaism:
`SKWJER` was glossed as a phonetic *skewer*, `QUNGLAYIM` as *quench lay him*,
`ORD. Q. BOOM` as *Ordnance Quartermaster Boom*. For PK8 it offered a
"plaintext candidate" beginning `NRHPXXOEICEJAANOSSOYBUIFLBVVOGFUNOITTHSE`
and reported "71.2% lexical word coverage", counting hits like `ICE`, `FUN`,
`SET` and `DAW`. For PK10 it read the letters `KCOLDYX` off a recovered wheel
and announced the mnemonic `COLD LOCK`.

Every one of those is the same error: **a measurement was substituted for a
judgement.** Short words appear in random text. A score can be maximised by
noise. An anagram of a suggestive phrase can be found in almost any string if
you are willing to move enough letters.

The claims are withdrawn. PK8, PK9 and PK10 are unsolved here.

How it happened is the useful part, and it is not stupidity — it is the
structure of the task. The searcher returns a best candidate whatever you feed
it, the score is genuinely higher than the alternatives, and the human reads the
fragments that look like words while skipping the ones that do not. The defence
is procedural: fix in advance what would count as a solution, and prefer tests a
wrong answer *cannot* pass — the anagram test of Chapter 3, the annihilator of
Chapter 7, an exhaustive enumeration that returns nothing.

### PK8 (N = 153): what is now ruled out

PK8 was solved externally in 2026 by Kevin Hu, after eighty-six days. The key
was never published, so it remains open *here*.

The author's hints: the algorithm is simple; the key has a lot of entropy but
some structure; and solving PK9 would probably help with PK8.

What this project established, with the method in brackets:

| Finding | Basis |
| --- | --- |
| **Not a two-wheel clock.** Every short wheel of 3–4 letters exhaustively (474,552 keys per shape), word lists for 5–10, every long wheel 3–16, both alphabets, 851 s. Best reading −5.87 against English −4.3, from a 24-unknown shape on 153 letters — overfitting. | exact enumeration |
| **Not recoverable by annealing** under the four-wheel hypothesis, even with the shape known. | 0 of 6 synthetic recoveries |
| **Falls instantly to a 19-letter crib** — if the crib is right. | 5 of 5 synthetic, 0.1 s |
| **No crib found** among ~1,800 candidates: every 19-letter window of the PK1–PK7 plaintexts plus the repository's crib lists, six wheel shapes, both alphabets. | exhaustive sweep |
| **Plaintext is not a passage from Hendrie's Theophilus** (*De Diversis Artibus* Book III, 1847 translation — the metalworking treatise that matches the story's subject). 587,666 letters over both alphabets, exact scan: nothing. Partial scan, which tolerates OCR damage and quotations that run out: longest run 5 constraints against about 4 by chance. | annihilator scan |
| **A modern translation is untested.** The repository's copy is Hendrie 1847; the standard modern renderings (Hawthorne & Smith 1963, Dodwell 1961) are in copyright and could not be obtained here. Two translations of the same Latin share almost no letter sequences, so this remains a genuinely open avenue — and a cheap one, since the scan settles a whole book in about a second. | not tested |
| **The PK plaintexts are original prose, not quotations.** Longest verbatim overlap between any PK1–PK7 plaintext and Theophilus: 14 letters (`TOTHEHEARTHAND`) — ordinary English, not borrowing. | substring search |
| **The wheel hypothesis cannot be confirmed statistically.** Across ten wheel-set hypotheses the log-likelihood ratios span 0.44 nats. Noise. | annihilator distribution test |

The last two entries are the ones a future attacker should read first. They cost
nothing to establish and they close off two attractive avenues.

### PK9 (N = 144): the identifiability wall

PK9's structure is believed to be an inner double columnar transposition with an
outer period-28 substitution. The outer layer looks attackable: a transposition
does not change *which* letters are present, so the text under the substitution
must have an English letter distribution, and a period-28 substitution built
from a 4-clock and a 7-clock has only 11 unknowns.

It does not work, and the measurement says why. On synthetic instances of that
exact shape, with the answer known:

```
true key,  monogram chi-squared score:  −23.07
best wrong local optimum:               −18.44
was the true key even a local optimum?   no
```

Wrong keys **fit the letter histogram better than the right one**. This is not a
search failure to be fixed with more restarts; it is an identifiability failure.
A letter histogram carries on the order of 25 degrees of freedom of information;
ten unknown dimensions over Z/26 need about 47 bits. The statistic is too small
for the question.

Breaking PK9's outer layer requires a statistic that survives transposition
**and** discriminates. Letter frequencies survive but do not discriminate;
n-grams discriminate but do not survive. That is the wall, stated precisely.

### PK10 (N = 504): a caution about scores

PK10 is believed to be a three-clock system with periods 7, 8 and 9 — combined
period lcm = 504, exactly the message length — composed with a transposition.

A run of the general solver reported a fitness of −5.53 against a previously
recorded best of −7.62, which reads like a record. It is not. The −5.53 came
from a chain that decoded **17 letters of the 504**, and per-character fitness
is only comparable at equal coverage. The scoring harness now refuses to print
that comparison below 95% coverage.

It is a small bug with a large moral, and it is the same moral as the
retraction: the number was correct, the comparison was meaningless, and nothing
but a human asking "of how much text?" would have caught it.

---

# Part IV — Apparatus

## Chapter 10: Reproducibility

Every factual claim in this book is produced by code in the repository.

```bash
# The scorecard: which challenges the solver reproduces, from ciphertext alone
python3 scripts/kryptos_ctf.py --budget 150

# Rebuild the explorer's data, verifying every solved entry
python3 scripts/build_kryptos_app_data.py

# Scan a corpus for a suspected plaintext (the annihilator of Chapter 7)
python3 scripts/sumclock_corpus_scan.py PK8 --periods 4,5,6,7 some_book.txt

# The solver's own honesty checks, and the test suite
python3 -m buttcrack selftest
python3 -m unittest discover -s tests -t .
```

The explorer's data build is the model this book would like to see used more
widely: it decrypts every solved entry with its published key and refuses to
emit one that does not reproduce its published plaintext. That check found seven
fabricated ciphertexts in the app this book accompanies — entries padded to
length with a repeating block, and one containing the literal text
`Duplicate...[truncated]`. Nothing had noticed, because nothing had ever tried
to use them.

## Chapter 11: What would move this forward

**For PK8.** A correct nineteen-letter crib ends it in a tenth of a second. The
crib must be *content*: a phrase actually in the plaintext. Failing that, the
open structural question is whether the four-wheel hypothesis is right at all —
it is inherited from prior analysis and has never been confirmed.

**For PK9.** A discriminating statistic that survives transposition. One
candidate: the inner text is not merely a permutation of English but a
*columnar* permutation, so letters that were adjacent in the plaintext remain a
fixed stride apart in the ciphertext. A statistic built on stride-k bigrams
might survive where the histogram does not. Untested.

**For PK10.** Establish coverage before comparing any score to any record.

**For K4.** Nothing in this book helps, and readers should be suspicious of
anyone who says otherwise.

---

### Colophon

Written against commit-level evidence in `ahardkore/Buttcrack---Cipher-Breaker`.
The solver described here implements 50 ciphers, reproduces Kryptos K1 and K2
from the published keys, and breaks Paradigm Kryptos PK1, PK2 and PK3 from
ciphertext alone. It does not break K4, PK8, PK9 or PK10, and says so on every
page where the question arises.
