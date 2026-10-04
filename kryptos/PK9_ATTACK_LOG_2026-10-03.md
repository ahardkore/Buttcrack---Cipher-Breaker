# PK9 adaptive attack log — 2026-10-03

## Attempt 1: proposed double-columnar candidate (FAIL)

The repository's `pk9_solution_pt.txt` candidate was tested with an exact
round-trip-derived keystream check under its claimed architecture:

- padded plaintext length: 144
- transposition geometry: 18x8 then 8x18
- outer schedule: period 28
- result: **113/144 schedule mismatches**
- derived first 28 shifts: `20,15,10,6,21,7,0,11,21,22,4,11,13,3,18,11,11,8,6,14,3,22,1,23,2,10,5,11`

This is a hard failure, not a language-score disagreement. The candidate is
not a solution and is excluded from subsequent work.

## Attempt 2: joint shift/permutation defect minimization (FAIL / plateau)

Compiled and ran `attack_pk9_full_defect_solver.c` with 2 threads, 30
restarts, and 3,000 steps/restart. It remained at:

- 11 invalid quadgrams out of 120
- normalized raw score: -5.3707
- 90.8% valid quadgrams
- no improvement over the seeded state

This is an optimization plateau and is not evidence of plaintext. The score
is retained as a negative result because defect penalties can overfit
transposition structure.

## Pivot selected

The next attack must stop treating the seeded 18x8/8x18 geometry as a fact.
The exact-test harness is `pk9_pivot_attack.py`. The next campaign should
jointly enumerate or anneal:

1. all factor geometries of 144 (not only 18x8 and 8x18);
2. both transposition composition orders;
3. period-28 substitution, Q5+Q6+Q7 sum-clock, and unrestricted periodic
   schedules;
4. a round-trip check before accepting any readable candidate.

No PK9 break is claimed by this log.

## Attempt 3: all factor-grid transposition annealing on fixed Z stream (FAIL)

The seven factor widths 6, 8, 9, 12, 16, 18, and 24 were searched with
2,000 random restarts each. Best scores ranged from -6.98 to -5.65; the
best was width 24 at -5.6539. Outputs remained gibberish/anagram plateaus.
Because the Z stream was generated from a seeded period-28 schedule, this
rules out neither other schedules nor joint models. It is recorded as a
negative transposition-only pivot.

## Attempt 4: classical-family harness (FAIL: invocation/environment)

The harness was invoked from the repository root but expects its data file in
its own directory, so it failed before testing with FileNotFoundError for
`pk_all_ciphertexts.json`. This is an execution failure, not cryptanalytic
evidence. It remains a queued pivot with corrected working-directory
invocation.

## Attempt 5: classical-family harness rerun (FAIL)

The missing `words_alpha.txt` dependency was supplied non-destructively from
the repository's `all_words.txt` vocabulary. The harness completed its
Autokey search over the first 5,000 dictionary candidates and found **zero
hits**. Results are in `pk9_classical_pivot_results.log`. The temporary
symlink was removed afterward.

## Repository audit while campaign runs

`pytest` is not installed in the environment. A fallback `python -m unittest
discover -s tests -q` invocation exceeded the 180-second command budget and
was terminated; no test process remained afterward. This is an infrastructure
limitation, not a passing test result. The focused Python compilation, shell
syntax, exact pivot check, and wheel-engine self-test remain independently
passing.

## Campaign interruption audit

The long-running R5 process is no longer present. Its log contains only the
stage header and no completion line, score, or candidate. This is therefore
classified as **INTERRUPTED / NO RESULT**, not as a negative cryptanalytic
result. The campaign runner's stage wrapper correctly would have written a
completion marker if the stage exited normally.
