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

Working hypothesis: a polyalphabetic substitution over a double columnar
transposition, the substitution period around 28 and the grids 18x8 and 8x18.
144 = 12 x 12 also factors conveniently, and both readings have been tried.

Best readings reached here: -4.93 with 71% word coverage
(`pk9_solution_pt.txt`), -4.85 with 59% (`pk9_solution_plaintext.txt`). Both
are below what a real solve looks like and are consistent with an over-fitted
transposition search rather than a recovered key.

The useful negative result is about method, not about PK9's key:

- A letter histogram cannot identify a substitution laid over a transposition.
  Measured on synthetic instances of the same shape, the true key scores
  -23.07 on monogram chi-squared while wrong local optima reach -18.44, and
  the true key is not even a local optimum. Monogram-guided search for the
  outer layer is a dead end. It needs a statistic that survives transposition
  and still discriminates, and letter frequencies are not it.

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
