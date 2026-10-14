# Reading candidate decryptions

The local cipher-breaker results panel shows **up to ten actual candidate
readings**, including the leader. Choose **Top 5** or **Top 10** without rerunning
the search. Each candidate has its full raw plaintext in a scrollable block,
cipher family/title, decode chain, reported key, structured parameters, score
measurements, ranking explanation and verification status. Supplied-key hints
are not silently treated as newly recovered secrets.

## Statistical plausibility is not verification

The panel distinguishes:

- **Rank score**: the engine's language/evidence score, not a probability that a
  candidate is correct. The API's legacy `confidence` and `solved` fields remain
  compatible; `solved` still means a language threshold was crossed. The panel
  calls that **statistically strong — not proven** rather than a verified solve.
- **Language plausibility**: the attached model's score before attack/evidence
  caps or canonical-corpus overrides. N-gram fitness and dictionary coverage
  help explain it. Dictionary coverage is marked **not assessed** when the
  attack/model did not use that view; absent dictionary scoring is not a failed
  English test. Word breaks are model suggestions, not historical evidence.
- **Round-trip reproduction**: direct candidates are re-encrypted with their
  reported key. Exact-character checks and normalized A–Z-only comparisons are
  explicitly distinguished. A mismatch is visible. A wrong key's corresponding
  wrong plaintext can still reproduce the ciphertext; reproduction does **not**
  prove the key, cipher attribution or intended message.
- **Canonical corpus match**: an exact normalized PK1–PK10 association checks the
  candidate plaintext and construction against the stored record. The corpus's
  documented verification and digest are shown. This is archive recognition,
  not a new statistical solve or an independent recheck performed in this run.
- **Not checked**: a live re-encryption check was not available. In particular,
  layered reports do not retain all outer keys, so no full-chain round trip is
  claimed. A note saying “verified” alone cannot promote a reading.

Generic candidate reports never claim independent verification or proof of
intended plaintext from language scores or from a passing round trip.

## Why one reading ranks above another

The actual ordering is lexicographic, not a sum of all displayed diagnostics:

1. Language/evidence rank score rounded to 0.001.
2. N-gram fitness rounded to 0.1.
3. Quality of the recovered opening word.
4. Fewer decoding layers.
5. Shorter rendered key.
6. Canonical naming preference among equivalent ciphers.

The explanation identifies the first criterion that separates a candidate from
its predecessor; the leader is compared with its runner-up. Exact ties retain
encounter order, which is not evidence. IC, chi-squared and segmentation are
additional diagnostics—not extra independent ranking votes or proof.

When no candidate crosses the statistical solve bar, strong cipher
identification may alter the leading attribution. That override is shown rather
than pretending its language score was highest. A negative score gap to the
leader makes the difference explicit. Equivalent cipher/key explanations and
short-text caveats appear in the evidence notes.

## Close competitors

A **close-score competitor** has an absolute rank-score difference of at most
**0.03**. The panel shows close peers for every candidate and identifies readings
close to the leader. This is a display heuristic, **not a calibrated probability,
confidence interval, or uniqueness test**. Two weak readings can be equally close
and equally unconvincing. Even a wide margin does not prove the leading message.

## Comparison search versus fast search

The browser enables **compare alternatives** by default. It continues past a
high language-score reading within the selected time budget, instead of stopping
at the first confident-looking answer. Individual attacks may still prescreen,
prune, yield only a shortlist, or return one reading. This is not exhaustive
cryptanalysis and cannot guarantee five or ten plausible candidates.

Uncheck the comparison option for the original fast behavior. Cancellation still
uses the normal Stop button. Exact canonical archive matches intentionally return
one stored reading instead of inventing competing decryptions.

Only returned candidates are shown. Fewer than five, missing diagnostics and
unchecked verification are stated explicitly. Identical normalized plaintexts
are merged, but candidates that merely share their first 160 letters are now
retained if their later text differs.

API: `POST /api/crack` accepts `compare: true` and `candidates: 10`. The returned
report includes `candidate_comparison`, and each candidate adds `family`,
`key_data`, `parameters`, `statistical_plausibility`, `ranking`, and `verification`.
Plaintext truncation for transport does not change the full-input verification.

Python: `solve(ciphertext, compare=True, budget=30)` or `Solver(compare=True)`.
CLI: `buttcrack --file ciphertext.txt --compare --candidates 10 --json`.
