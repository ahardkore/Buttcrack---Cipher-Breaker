# K4 Negative Results — 2026-10-05

Reproducible eliminations from the renewed K4 attack. Every search in this document was validated against **planted ciphers** before its negative result was accepted: a search that finds nothing is only meaningful if it can find something.

Raw output is in [`results/`](results/). Nothing here is a solve; all of it is pruning.

> **Revision 2026-10-04 — read §3e first.** This round added the keyed-alphabet sweep (§3d), which refutes **Quagmire III — the cipher K1 and K2 themselves use — by proof, over all 26! alphabets at every period**. It also uncovered a counting defect shared by the three earlier harnesses: **328,962 configurations had been reported as eliminated without ever being read.** All of them have now been decided and all of them fail, so no verdict in this document changed. But §3, §3b and §3c had been resting on evidence that did not exist, and their numbers have been corrected in place.

---

## 1. Structural keystream hypotheses — eliminated

Tested against the 24 artist-confirmed (position, shift) pairs. Each is an exhaustive search, not a sample.

| Hypothesis | Space searched | Result |
|---|---|---|
| Polynomial keystream, degree 1 | all 26² coefficient sets | no fit |
| Polynomial keystream, degree 2 | all 26³ | no fit |
| Polynomial keystream, degree 3 | all 26⁴ | no fit |
| Clock counter, Weltzeituhr 24 zones | all offsets × 120 phases | no fit |
| Clock counter, 12h/60m | ″ | no fit |
| Clock counter, Mengenlehreuhr rows (4,4,11,4) | ″ | no fit |
| Clock counter, 24h/60m/60s | ″ | no fit |
| Clock counter, base 5 | ″ | no fit |
| Linear congruential, shift[i+1] = a·shift[i] + b | all 676 (a,b) | no fit |

The clock-counter family was worth testing specifically because `CLOCK` is a confirmed crib and Sanborn confirmed in November 2025 that it denotes the Weltzeituhr. A mixed-radix counter is the natural keystream a clock suggests. It does not fit.

## 2. Transposition × monoalphabetic substitution — impossible by invariant

Not a search; a proof.

Index of coincidence is invariant under transposition (it only reorders letters) **and** under monoalphabetic substitution (it only relabels them). Therefore any composition of the two preserves it.

| | IoC |
|---|---|
| English | 0.0667 |
| K4 | **0.0361** |
| uniform random | 0.0385 |

K4's IoC sits at the random floor. No transposition composed with a monoalphabetic substitution, in either order, under any key, can produce it from English. **The substitution stage must be polyalphabetic.** This is what motivated §3.

## 3. Transposition × periodic polyalphabetic — eliminated

The largest family never tested here. Harness: [`attack_k4_composite.py`](attack_k4_composite.py).

### Why it became testable

The repository's own note on PK4–PK6 says a transposition's key "cannot be scored while the text underneath is still enciphered." **For K4 that deadlock breaks.** Sanborn released 24 plaintext letters at known positions, so a candidate permutation can be scored directly on whether the cribs stay arithmetically consistent — without reading the text underneath.

For each (columns, column order, composition order, alphabet) the 24 cribs give 24 (key index, required shift) pairs. Bucket them by index mod p; any bucket holding two different shifts is a contradiction and the configuration dies.

### Models

- **Case A** — `C = T(V(P))`, substitute then transpose
- **Case B** — `C = V(T(P))`, transpose then substitute
- `T` = classical columnar transposition, row-wise fill, arbitrary column read order
- `V` = periodic polyalphabetic shift, period 1–26, over the standard **and** KRYPTOS-keyed alphabets

### Validation

```
PASS  case=A cols=5 period=3 alpha=standard   crib-consistent  key-agrees  decrypts
PASS  case=B cols=7 period=4 alpha=KRYPTOS    crib-consistent  key-agrees  decrypts
PASS  case=A cols=4 period=2 alpha=KRYPTOS    crib-consistent  key-agrees  decrypts
PASS  case=B cols=6 period=5 alpha=standard   crib-consistent  key-agrees  decrypts
Negative control: 119/119 wrong column orders correctly rejected
```

> **Corrected 2026-10-04.** The "crib-consistent" columns in both tables below are wrong — they were counted *after* the `--max-unknown` filter and so report only the configurations that were cheap enough to read. The true counts are **31,134** (exhaustive) and **12,653** (keyword), of which 22 and 18 were read. All 43,747 have since been decided and all fail; see §3e. The verdict stands, the original evidence for it does not.

### Results — exhaustive column orders

**42,547,648 configurations, 51.2s.** 31,134 crib-consistent, of which these were read at the time:

| L | orders | read (reported then) | true crib-consistent |
|---|---|---|---|
| 2 | 2 | 0 | 0 |
| 3 | 6 | 0 | 2 |
| 4 | 24 | 0 | 0 |
| 5 | 120 | 0 | 16 |
| 6 | 720 | 0 | 42 |
| 7 | 5,040 | 0 | 696 |
| 8 | 40,320 | 18 | 2,444 |
| 9 | 362,880 | 4 | 27,934 |
| **Total** | **409,112** | **22** | **31,134** |

### Results — dictionary-keyword column orders

Classical columnar keys are words. Numbering a keyword's letters alphabetically gives the column order, which reaches lengths exhaustive `L!` enumeration cannot — notably **L=14, the width Sanborn actually used in K3**.

**17,202,952 configurations, 23.3s.**

| L | orders | read | true | | L | orders | read | true |
|---|---|---|---|---|---|---|---|---|
| 4 | 24 | 0 | 0 | | 11 | 27,468 | 1 | 1,839 |
| 5 | 120 | 0 | 16 | | 12 | 21,368 | 10 | 1,519 |
| 6 | 720 | 0 | 42 | | 13 | 15,430 | 1 | 1,095 |
| 7 | 4,893 | 0 | 682 | | **14** | **10,063** | **0** | **834** |
| 8 | 20,014 | 6 | 1,249 | | 15 | 315 | 0 | 27 |
| 9 | 32,100 | 0 | 2,365 | | 16 | 123 | 0 | 13 |
| 10 | 32,775 | 0 | 2,972 | | **Total** | **165,413** | **18** | **12,653** |

### What the survivors are

*(This described the 22 survivors that were read. It holds for all 31,134 once they were decided in §3e — the best of them reaches −6.58 against English −4.04, still an overfit, still clustered at long periods.)*

Every survivor is an overfit, and they fail in a diagnostic way. All sit at period 23 or 26 — long enough that 24 cribs pin nearly every key residue. They reproduce `EAST NORTHEAST` and `BERLIN CLOCK` exactly and emit noise everywhere else:

```
cols=12 key=UNSEIGNORIAL case=B period=26   quadgram -622
ESJLPIUREARODYANTBXYWEASTNORTHEASTASDMAUOFUVEZIOJNQUHLSTXTGKMKSBERLINCLOCKPTSHYFCJFOWUANHPWJWBALX
```

Fluent 97-letter English scores about **−391**; the best survivor scores **−622**. This is the identical failure mode as the period-29 Vigenère in `kryptos_solve.py`: when the key is nearly as long as the known plaintext, "fitting the cribs" means only "copying the cribs."

**Verdict: eliminated** for all column orders with L ≤ 9, for all dictionary-keyword orders with L ≤ 16, period ≤ 26, both composition orders, both alphabets.

## 3b. Route / geometric transposition × periodic polyalphabetic — eliminated

K3 was columnar, but Scheidt described a deliberate *"change in the methodology"* for K4, so the non-columnar families a hand encipherer would reach for got their own sweep. 97 is prime, so every grid is ragged.

**445 distinct permutations, 46,280 configurations, 1.9s.** **153** crib-consistent, all overfits. *(Originally reported as 124 — the post-filter count. The remaining 29 were decided in §3e and also fail; best −7.32. This is the one sweep where most of the survivors had in fact been read.)*

| Family | permutations |
|---|---|
| Spirals (4 corners × 2 directions, w=2..48) | 188 |
| Rows boustrophedon | 47 |
| Columns plain | 47 |
| Columns boustrophedon | 47 |
| Diagonals | 47 |
| Antidiagonals | 47 |
| Rail fence (2–24 rails) | 22 |

Self-tested on planted rail-fence, spiral, and diagonal ciphers in both composition orders — 6/6 recovered. Best survivor scores **−583** against −391 for fluent English, again at period 25, again copying the cribs and emitting noise.

---

## 3c. Aperiodic and progressive keystreams — eliminated outright

Harness: [`attack_k4_aperiodic.py`](attack_k4_aperiodic.py). Every periodic model being dead, the classical next move is a key that *advances* rather than repeats. Self-tested on four planted progressive ciphers; negative controls rejected 24–25 of 25 wrong step values each.

### Running key

The cribs hand us the key directly at 24 positions, so the family can be tested without guessing the source text — a running key drawn from prose must *look* like prose.

| Alphabet | Convention | Fragment @22–34 | score | Fragment @64–74 | score |
|---|---|---|---|---|---|
| standard | Vigenère | `BLZCDCYYGCKAZ` | −9.24 | `MUYKLGKORNA` | −8.11 |
| standard | Beaufort | `JLJODEGKUKKKL` | −8.64 | `OCGGBGOKTRU` | −7.52 |
| KRYPTOS | Vigenère | `RDUMRIYWOYNKY` | −8.35 | `ELYOIECBAQK` | −7.61 |
| KRYPTOS | Beaufort | `WXAKGZTOAXAFD` | −8.17 | `RGTGNWRJLFK` | −8.83 |

English prose scores about **−2.4**; uniform noise about **−5.2**. Every fragment lands *below the noise floor*. No running key drawn from natural language can produce these shifts.

### Digit-limited keystreams (Gromark, Gronsfeld, Nihilist)

These add decimal digits, so every shift must be 0–9. One crib above 9 kills the family.

| Alphabet | Convention | Max shift | Cribs over 9 |
|---|---|---|---|
| standard | Vigenère | 25 | 15/24 |
| standard | Beaufort | 20 | 14/24 |
| KRYPTOS | Vigenère | 23 | 11/24 |
| KRYPTOS | Beaufort | 25 | 14/24 |

Eliminated under every alphabet and convention.

### Progressive and position-linear keys

`K[i] = base[i mod p] + step·(i div p)` and `K[i] = base[i mod p] + step·i`, exhaustive over p = 1..30, step = 0..25, both conventions, both alphabets, both drift modes.

> **Corrected 2026-10-04.** This subsection previously reported **0 crib-consistent** configurations in both rows and called the family "a cleaner kill than the periodic sweep," on the grounds that nothing survived at all. That was wrong. The number came from a counter incremented *after* the `--max-unknown` filter, so it reported what had been **read**, not what had been **refuted**. The true figures are below. The family is still eliminated, but on different evidence, and the "cleaner kill" claim is withdrawn. See §3e.

| Sweep | Configurations | Crib-consistent | Decided | Undecided |
|---|---|---|---|---|
| Identity transposition | 6,240 | 628 | 628 | **0** |
| × all 445 geometric transpositions | 2,776,800 | 284,558 | 284,558 | **0** |
| **Total** | **2,783,040** | **285,186** | **285,186** | **0** |

So the drift term does *not* kill the family outright — 285,186 configurations reproduce all 24 anchors. They are eliminated on the text they produce, decided by masking the free residues and excluding every quadgram that touches an anchor. Best result **−6.39** against fluent English −4.04 and raw ciphertext −7.74: 36% of the way from noise to English, and sitting at p = 28–29, the overfit band. Nothing was skipped.

## 3d. Keyed alphabets (Quagmire I–IV) — Quagmire III refuted by proof

Harness: [`attack_k4_quagmire.py`](attack_k4_quagmire.py). Output: [`results/k4_quagmire.txt`](results/k4_quagmire.txt).

### The gap this closes

Every sweep above was exhaustive over *keys* but fixed the *alphabet* to one of two: standard A–Z, or the sculpture's KRYPTOS-keyed tableau. Quagmire ciphers key the alphabets themselves, which changes the index mapping and so escapes all of it.

This is also where the misspelling hypothesis finally gets a fair test. A specific key proposal cannot revive a family already swept exhaustively over all keys — those sweeps already tried whatever IQLUSION would have produced. The misspellings can only matter if they select a **mechanism** rather than a key, and the obvious mechanism is a keyed alphabet. So they enter here, as alphabet keywords, which is the one place they can still do work. They do none.

### Two layers, and the first is a proof

`C[i] = A_c[(A_p.index(P[i]) + k[i mod p]) mod 26]`, so each crib gives `k[i mod p] = A_c.index(C[i]) − A_p.index(P[i])`. The key is solved for, never guessed.

When two cribs share a residue they must imply the same shift. Sometimes that requirement collapses, after cancelling a letter, to `x[a] = x[b]` with `a ≠ b` — which **no permutation can satisfy**, so the period dies for every conceivable alphabet:

| Model | Periods refuted for all 26! ≈ 4.0 × 10²⁶ alphabets |
|---|---|
| Quagmire I | 8 of 26 — p = 1, 2, 3, 4, 5, 9, 15, 17 |
| Quagmire II | 13 of 26 — p = 1, 2, 3, 5, 6, 7, 9, 10, 14, 15, 17, 21, 25 |
| **Quagmire III** | **26 of 26 — every period** |

**Quagmire III is the cipher K1 and K2 actually use, and it is now refuted outright for K4.** Two independent obstructions do it. Positions 22 and 31 both decrypt from plaintext `E` but carry different ciphertext letters (`F` and `G`), forcing `x[F] = x[G]`. And position 74 is the famous `K→K` fixed point, which forces a zero shift that no other crib sharing its residue can match. Because Quagmire III uses one alphabet on both sides, neither can be absorbed. This is a proof over all 4.0 × 10²⁶ alphabets, not a sample of 30,000.

### Deciding the long periods without enumerating them

The 24 cribs sit at 0-indexed 21–33 and 63–73. For p ≤ 13 and p ∈ {15,16,17} they touch every residue. For the rest some residues are free — p = 21 leaves 8, which is 26⁸ ≈ 2.1 × 10¹¹ fills per configuration. Unreachable.

An earlier version of this script enumerated those fills and **skipped** any configuration with more than `--max-unknown` free residues, then reported the skipped ones as though they had been refuted. That is the one error this project cannot afford, and it is fixed rather than papered over: a free residue only darkens the positions congruent to it, and every other letter is already determined. Masking the dark positions still leaves 30–64 scorable quadgrams at every period. If the determined letters are not English, no assignment of the free residues can make them English — those letters do not move.

Scoring additionally **excludes every quadgram touching an anchor**, so the 24 crib letters earn no credit. This is the long-period overfit guard; it has caught this project four times. Removing that free credit dropped the best candidate from −5.86 to −6.58, confirming the anchors had been inflating it.

### Results

30,000 distinct keyed alphabets (38 sculpture-nominated, including every misspelling-derived variant), periods 1–26.

| Model | Configurations | Crib-consistent | Decided | Undecided |
|---|---|---|---|---|
| Quagmire I | 780,000 | 5,684 | 5,684 | **0** |
| Quagmire II | 780,000 | 36 | 36 | **0** |
| Quagmire III | 780,000 | **0** | 0 | **0** |
| Quagmire IV | 29,640,000 | 45,336 | 45,336 | **0** |
| **Total** | **31,980,000** | 51,056 | 51,056 | **0** |

Nothing was skipped. Every crib-consistent configuration was decided on evidence no choice of free residues can alter.

Best candidate, after fully enumerating the 210,912 completions of the shortlist:

```
-6.39  Quagmire IV  pt=ILLUSION ct=BUMPERETTE p=26
SMOLIDAQIODAGEYEGMUTLEASTNORTHEASTBYOWNETHRIADOZGNNIIAMNGYNHAUCBERLINCLOCKGDCLEHVEBIWFORTPRPEDBHB
```

Fluent English is −4.04 per crib-free quadgram and the raw ciphertext −7.74, so the best Quagmire in 32 million sits **37% of the way from noise to English** — and, predictably, at p = 26, the overfit band.

### Validation

Self-test: **22 PASS / 0 FAIL** ([`results/k4_quagmire_selftest.txt`](results/k4_quagmire_selftest.txt)).

- Four planted ciphers recovered and decrypted exactly; 29/29 wrong plaintext alphabets contradicted.
- **The critical test** — at each of p = 14, 18, 19, 20, 21, 22, 23, 24, 25, 26, a planted cipher is recovered from masked evidence alone against 3,998 decoys. At p = 26, 624 decoys survive the crib algebra and the masked score beats all of them (true −4.09, best decoy −6.20). Removing anchor credit *widened* that margin, which is the correct direction.
- **Soundness of the analytic layer**: four demonstrably-existing planted ciphers, including a Quagmire III at p = 26, are never flagged impossible. The proofs produce no false positives.

### Scope, stated precisely

The analytic half is a proof over all alphabets. The empirical half is a *dictionary* sweep, so it rules out word-keyed alphabets, not arbitrary permutations. Quagmire I, II and IV over the full 26! permutation space remain formally open; only Quagmire III is closed completely.

## 3e. Audit correction — 12,664 configurations were counted as eliminated but never read

Harness: [`decide_undecided.py`](decide_undecided.py). Outputs: [`results/k4_decide_undecided.txt`](results/k4_decide_undecided.txt) (keyword orders), [`results/k4_decide_undecided_exhaustive.txt`](results/k4_decide_undecided_exhaustive.txt) (L≤9).

**This section corrects §3, §3b and §3c.** Building the Quagmire sweep exposed a reporting defect that every earlier harness shared, so all of them were re-audited rather than left alone. The defect did not change a single verdict, but it invalidated the stated evidence for three of them.

### The defect

`attack_k4_composite.py` filters on `--max-unknown`: if the 24 cribs leave more than N key residues free, enumerating the fills costs 26ᴺ decrypts, so the configuration was dropped. The counter that was labelled *crib-consistent survivors* was incremented **after** that filter. Configurations that were never read were therefore reported in the same breath as configurations that had been read and refuted.

Skipped is not eliminated. The scale of it:

| Sweep | Crib-consistent | Actually read | **Never read** | Read |
|---|---|---|---|---|
| Route / geometric (§3b) | 153 | 124 | **29** | 81% |
| Exhaustive column orders L≤9 (§3) | 31,134 | 22 | **31,112** | 0.07% |
| Dictionary keyword orders L≤16 (§3) | 12,653 | 18 | **12,635** | 0.14% |
| Progressive / position-linear (§3c) | 285,186 | 0 | **285,186** | **0%** |
| **Total** | **329,126** | **164** | **328,962** | **0.05%** |

Only the route sweep was substantially read. The two columnar sweeps in §3 had read well under 1% of what reproduced the anchors. And §3c had read **none at all**: its headline "ZERO crib-consistent" was the post-filter count, so a family with 285,186 anchor-reproducing configurations was written up as one where "nothing survives at all."

The common cause is a single misplaced line. In each harness the survivor counter sat below the `if len(unknown) > max_unknown: continue` guard instead of above it, which silently redefined "crib-consistent" as "crib-consistent **and** cheap enough to enumerate."

### Deciding them without enumeration

Each plaintext position depends on exactly one key residue. Decrypt twice, filling the free residues with 0 and then with 1: positions fed by a free residue shift by one letter and differ, positions the cribs determine cannot. The disagreement set is *exactly* the undetermined set — an identity, verified against ground truth in the self-test, not a sample. Score only quadgrams avoiding those positions and avoiding the 24 anchors.

| Stage | Previously skipped | Decided by masking | Decided by exact enumeration | Best |
|---|---|---|---|---|
| Route / geometric (§3b) | 29 | 29 | — | −7.32 |
| Exhaustive L≤9 (§3) | 31,112 | 31,109 | 3 | −6.58 |
| Dictionary keywords L≤16 (§3) | 12,635 | 12,631 | 4 | −6.58 |
| Progressive / linear (§3c) | 285,186 | 285,186 | — | −6.39 |
| **Total** | **328,962** | **328,955** | **7** | **−6.39** |

Seven cases had too few determined letters to mask, so they were enumerated exhaustively instead — every fill, no cap, no shortlist:

| Config | Free | Fills enumerated | Best achievable |
|---|---|---|---|
| L=8 `AGUAVINA` case B, standard | 4 | 456,976 | −6.65 |
| L=8 `AIRDROME` case B, standard | 4 | 456,976 | −6.77 |
| L=12 `ALCOHOLICITY` case B, standard | 5 | 11,881,376 | −7.26 |
| L=12 `SARCOLOGICAL` case B, KRYPTOS | 5 | 11,881,376 | −7.01 |
| L=8 order `(0,3,7,1,5,6,2,4)` case B, standard | 4 | 456,976 | −6.65 |
| L=8 order `(0,3,7,1,6,5,2,4)` case B, standard | 4 | 456,976 | −6.77 |
| L=8 order `(0,7,2,6,5,1,4,3)` case B, KRYPTOS | 5 | 11,881,376 | −7.75 |

Fluent English is −4.04 per crib-free quadgram and raw ciphertext −7.74. The best of all 328,962 is −6.39, **36% of the way from noise to English**, and it sits at period 28 — the overfit band, as every near-miss in this project has.

### Outcome

**The verdicts of §3, §3b and §3c stand, but they did not stand on the evidence originally given for them.** They do now: zero configurations in these families remain unread, and every one of the 328,962 that had been skipped fails on its own crib-free letters.

Three changes make the defect non-recurring:

1. All three harnesses now report **tested / crib-consistent / decided / undecided** as four separate numbers, and print an explicit "NOT eliminated — undecided" warning whenever the last is non-zero.
2. Scoring excludes every quadgram touching an anchor, so no configuration can earn credit for reproducing cribs it was fitted to.
3. `--max-unknown` no longer gates elimination anywhere. It survives only to bound the optional exact-enumeration stage, which is now a fallback for cases masking cannot decide rather than the primary filter.

The honest summary of this round: **no verdict changed, and the searches were right, but three of them had been reported on evidence that did not exist.** A negative result is only worth what its accounting is worth.

## 4. What this leaves

Closed since the last revision: keyed-alphabet Quagmire ciphers (§3d), with Quagmire III refuted by proof rather than by search; and the misspellings-as-key-material hypothesis (§3d), which was the single most thematically motivated lead remaining and is now spent. The eliminations in §3, §3b and §3c were re-established on real evidence (§3e).

Still standing, roughly in order of promise:

1. **L ≥ 10 with non-dictionary column orders.** Exhaustive `L!` is infeasible past 10; needs branch-and-bound with incremental crib pruning. The most tractable of what remains.
2. **Double transposition** (keyword × keyword), reachable with the existing prune.
3. **Quagmire I, II, IV over arbitrary (non-word) alphabets.** 26! is far out of reach by enumeration, but the analytic layer in §3d extends — more periods may be refutable by proof without any search at all. Cheap to try, and it is the only technique here that scales to the full permutation space.
4. **Grilles and physical overlays.** Not expressible as a parameterised permutation family, so no existing harness reaches them.
5. **Hand methods with no clean algebraic form.** Sanborn: *"Who says it is even a math solution?"* Scheidt described masking techniques.

The pattern is now hard to ignore: **every family with a clean algebraic form has failed**, several of them by proof rather than by search. That is itself a result, and it points where Sanborn and Scheidt have both pointed.

## 5. K5 depth attack — tooling built and validated

Harness: [`k5_depth_attack.py`](k5_depth_attack.py). **Staged and self-tested, waiting on the ciphertext.**

Paradigm holds K5 and has said it will be released. Sanborn confirmed K5 is 97 characters, written at the same time, and *shares coded words in identical positions with K4*. If the keystream is additive and position-dependent, it cancels:

```
C4[i] − C5[i] = P4[i] − P5[i]        the key is gone, whatever it was
```

Three consequences, all implemented:

**Detection.** IoC of the difference stream, against the English-minus-English null (0.0397) versus random (0.0385). IoC is permutation-invariant, so **the test still fires even if a shared transposition sits on top of the shared keystream.**

**Free plaintext.** Sanborn released 24 letters of P4; wherever P4 is known, `P5[i] = P4[i] − D[i]`. 24 letters of K5 recovered before any cryptanalysis.

**Shared words self-locate.** "Coded words in identical positions" means `D[i] = 0` exactly where the two plaintexts agree. Runs of zeros *are* the shared words, visible without decrypting anything.

### Validation on synthetic depth

Two English plaintexts under one random 97-symbol keystream, keystream never shown to the attack:

| Step | Result |
|---|---|
| Depth detection | IoC(D) = 0.327 vs 0.0385 random — **DEPTH CONFIRMED** |
| Anchor propagation | 24/24 letters of P5 exact (`NORTHEAST` → `SOUTHEAST`) |
| Shared-span localisation | 2 spans found, both genuinely shared, zero false positives |
| Mutual crib drag | `BERLIN` recovered at its true position 64 |

One design note worth recording: the crib drag initially failed. Inside a `D == 0` run every word trivially implies itself and scores as perfect English while carrying no information, which swamped the ranking with ties. Masking the already-recovered zero spans is what makes the drag meaningful — the fix is in `zero_mask()`.

**On release day:** `python3 kryptos/k5_depth_attack.py --c5 <ciphertext>`

---

*Harnesses:* [`attack_k4_composite.py`](attack_k4_composite.py) (`--selftest`, `--keywords`, `--max-cols`), [`verify_k4_claim.py`](verify_k4_claim.py), [`backbuild_falsification.py`](backbuild_falsification.py).
