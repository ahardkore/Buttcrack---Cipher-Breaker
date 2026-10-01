# PK8, PK9 and PK10

None of these three is solved here. This file records what the ciphertexts
look like, what was tried, and what can be ruled out, so the next attempt does
not repeat the same ground. It replaces a set of longer reports that claimed
more than the evidence supported; see [AUDIT.md](AUDIT.md).

Scores below are quadgram fitness in log10 per character. English averages
about -4.3. The solved PK records sit between -4.2 and -4.45, so a reading at
-5.2 is not a partial solution, it is a search that has fitted noise.

## PK8, 153 letters

Structure, per the CTF: several short wheels added together over the KRYPTOS
alphabet, `K[t] = q4[t mod 4] + q5[t mod 5] + q6[t mod 6] + q7[t mod 7]`. The
period is lcm(4,5,6,7) = 420, longer than the message, so no two positions
share a key symbol and column-wise chi-squared has nothing to work with.

PK8 was solved by Kevin Hu after 86 days. The key was never published. Nothing
in this directory recovers it.

What was measured here:

- With a crib of 19 known letters the wheels fall out by linear algebra in
  about 0.1 seconds, five times out of five on synthetic instances. Nineteen
  is where the equations outnumber the nineteen effective unknowns (22 wheel
  letters, less one per wheel for gauge freedom).
- Shorter cribs need search: 16 letters recovered 4 of 4, 14 letters 2 of 4,
  12 letters 0 of 4.
- Without a crib, annealing for 60 seconds per instance recovered 0 of 6 and
  plateaued at -6.09 against a true-key -4.25. The landscape has almost no
  gradient, because every position's key is a sum of four unknowns and moving
  one coordinate earns no partial credit.
- A sweep of roughly 1,800 candidate cribs (every 19-letter window of the
  author's published PK1-PK7 plaintexts, plus the crib lists in this
  directory) across six wheel shapes and both alphabets found nothing. That is
  evidence about those cribs, not about the method.
- PK8 is not a two-wheel clock. The two-wheel solver is exact rather than
  heuristic, so this is elimination, not failure to find: every short wheel of
  three or four letters exhaustively (26^3 and 26^4 per shape), word lists for
  short wheels of five to ten, every long wheel from three to sixteen, both
  alphabets, 851 seconds in total. The best reading scored -5.87 and came from
  a {9,16} shape carrying 24 unknowns on 153 letters, which is overfitting.

The candidate stored in `pk_submission_manifest.json` is a failed attempt kept
for the record. It scores -6.43 with 8% coverage in words of four letters or
more. The clock parameters it names do reproduce it from the ciphertext, which
is why it survived review for so long: internal consistency is not the same as
a solution.

## PK9, 144 letters

Unsolved. What follows is what the ciphertext looks like, which hypotheses are
now eliminated, and why the scores previously recorded here were not evidence.

Ciphertext statistics: IC 0.0445 against 0.0667 for English and 0.0385 for
random; all 26 letters present; the letter distribution is nothing like
English (Q appears 8 times in 144 letters, 5.6% against English's 0.1%), so a
substitution of some kind is certainly present. Coset IC peaks at period 7
(0.0568) with harmonics at 14 and 21.

### What is eliminated

**Transposition followed by a short periodic shift.** A transposition cannot
change the index of coincidence, so if the cipher is `S(T(plaintext))` with
`S` a periodic shift, undoing `S` has to leave a text whose IC is the
plaintext's, about 0.066. The highest IC *any* choice of shifts can produce is
an upper bound on that, and it is computable: maximise IC by coordinate ascent
over the shifts. Over the KRYPTOS alphabet the ceiling is 0.0475 at period 4,
0.0546 at period 8 and 0.0631 at period 7 — all short of what English needs.
Longer periods clear 0.066 only by overfitting: at period 28 the same
procedure reaches 0.117 on this text and 0.106 on a shuffle of it, which is
the signature of fitting noise rather than finding a key.

**Substitution followed by an aligned columnar transposition.** If the grid
width is a multiple of the substitution period, every ciphertext column is a
single shift class, so each column should be an internally monoalphabetic
sample with English-like IC. Measured against 300 shuffles per width, no width
from 4 to 36 reaches even two standard deviations above its null, in either
the block or the stride convention.

**Hill, with or without a keyed alphabet.** The attack that broke PK7 finds
nothing here: best reading -6.14 against English's -4.3. The block-repeat
detector gives 7 aligned pairs of 2-letter blocks where 3.8 is chance, which
is not a signal.

**Sum-clock keys, at matched effort.** See below.

### Why the old "record" was not progress

This file used to quote a best score of -5.2493 as a frontier. Scores on a
144-letter text need a null before they mean anything, because a key with
enough freedom will fit noise. Running the sum-clock attack on PK9 and on four
shuffles of PK9 — same letters, no structure, same budget, same code:

| text | best fitness |
| --- | --- |
| PK9 | -6.01 |
| shuffle 1 | -6.09 |
| shuffle 2 | -6.06 |
| shuffle 3 | -6.10 |
| shuffle 4 | -5.99 |

The real ciphertext is inside the null distribution. Longer runs push both
numbers up together: a 600-second run on the real text reaches -5.47 with
23 unknown key letters against 144 letters of output, which is 0.28
confidence under the evidence rule and should be read as the search
describing itself.

`python3 scripts/null_floor.py --cipher sum_clock --pk PK9 --budget 120`
reproduces this, and will do the same job for any attack anyone tries next.
A reading on PK9 is worth attention when it beats the shuffles at the same
effort, and not before.

### What is still open

The period-7 family is the only structure that has shown anything at all: it
is the one period whose IC ceiling (0.0631) beats its own shuffle maximum
(0.0607), and the one whose pooled chi-squared fit (56.3) beats all ten
shuffles (best 58.8). Both margins are thin, both come from the same
statistic, and neither survives into a reading. It is worth one more look with
a model that is not a plain shift — the author's other puzzles use keyed
alphabets and summed wheels, and a period-7 wheel inside a larger composition
would show exactly this much and no more.

## PK10, 504 letters

Working hypothesis: three wheels of 7, 8 and 9 added over the KRYPTOS
alphabet, lcm(7,8,9) = 504, which is exactly the message length, laid over a
transposition on a 12x42 grid.

Best stored readings score between -6.2 and -6.6 with 20% to 27% word
coverage. They are not English. Treat the grid geometry above as an
assumption, not a finding: it comes from the length factoring neatly, which is
suggestive and nothing more.

## A note on the numerology

`verify_all_mathematical_theorems.py` prints a set of arithmetic identities
about these parameter sets, including one that recovers the sculpture's GPS
coordinates from sums of selected letters. The quantities and the moduli were
chosen after the fact. None of it was used to break anything, and none of it
should be treated as evidence about the ciphers.
