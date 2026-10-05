# K4 Negative Results — 2026-10-05

Reproducible eliminations from the first session of the renewed K4 attack. Every search in this document was validated against **planted ciphers** before its negative result was accepted: a search that finds nothing is only meaningful if it can find something.

Raw output is in [`results/`](results/). Nothing here is a solve; all of it is pruning.

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

### Results — exhaustive column orders

**42,547,648 configurations, 53.8s.**

| L | orders | crib-consistent |
|---|---|---|
| 2–7 | 5,912 | 0 |
| 8 | 40,320 | 18 |
| 9 | 362,880 | 4 |

### Results — dictionary-keyword column orders

Classical columnar keys are words. Numbering a keyword's letters alphabetically gives the column order, which reaches lengths exhaustive `L!` enumeration cannot — notably **L=14, the width Sanborn actually used in K3**.

**17,202,952 configurations, 23.3s.**

| L | distinct orders | crib-consistent | | L | distinct orders | crib-consistent |
|---|---|---|---|---|---|---|
| 4 | 24 | 0 | | 11 | 27,468 | 1 |
| 5 | 120 | 0 | | 12 | 21,368 | 10 |
| 6 | 720 | 0 | | 13 | 15,430 | 1 |
| 7 | 4,893 | 0 | | **14** | **10,063** | **0** |
| 8 | 20,014 | 6 | | 15 | 315 | 0 |
| 9 | 32,100 | 0 | | 16 | 123 | 0 |
| 10 | 32,775 | 0 | | | | |

### What the survivors are

Every survivor is an overfit, and they fail in a diagnostic way. All sit at period 23 or 26 — long enough that 24 cribs pin nearly every key residue. They reproduce `EAST NORTHEAST` and `BERLIN CLOCK` exactly and emit noise everywhere else:

```
cols=12 key=UNSEIGNORIAL case=B period=26   quadgram -622
ESJLPIUREARODYANTBXYWEASTNORTHEASTASDMAUOFUVEZIOJNQUHLSTXTGKMKSBERLINCLOCKPTSHYFCJFOWUANHPWJWBALX
```

Fluent 97-letter English scores about **−391**; the best survivor scores **−622**. This is the identical failure mode as the period-29 Vigenère in `kryptos_solve.py`: when the key is nearly as long as the known plaintext, "fitting the cribs" means only "copying the cribs."

**Verdict: eliminated** for all column orders with L ≤ 9, for all dictionary-keyword orders with L ≤ 16, period ≤ 26, both composition orders, both alphabets.

## 3b. Route / geometric transposition × periodic polyalphabetic — eliminated

K3 was columnar, but Scheidt described a deliberate *"change in the methodology"* for K4, so the non-columnar families a hand encipherer would reach for got their own sweep. 97 is prime, so every grid is ragged.

**445 distinct permutations, 46,280 configurations, 1.9s.** 124 crib-consistent, all overfits.

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

| Sweep | Configurations | Crib-consistent |
|---|---|---|
| Identity transposition | 6,240 | **0** |
| × all 445 geometric transpositions | 2,776,800 | **0** |

**This is a cleaner kill than the periodic sweep.** There, long periods produced crib-copying overfits that had to be dismissed on quadgram grounds. Here the drift term couples all 24 cribs to a single `step`, so nothing survives at all — the family cannot be made to fit even by brute force.

## 4. What this leaves

Still standing, roughly in order of promise:

1. **Aperiodic polyalphabetic over a composite.** Period ≤ 26 was the cap above. A running key or a long non-repeating key composed with transposition is untouched.
2. **Non-columnar transposition** — route, spiral, rail, grille. K3 was columnar, but K4 was explicitly a "change in methodology."
3. **L ≥ 10 with non-dictionary column orders.** Exhaustive `L!` is infeasible past 10; needs branch-and-bound with incremental crib pruning.
4. **The intentional misspellings as key material** — IQLUSION, UNDERGRUUND, DESPARATLY, the stray `?`s. Bounded space, strong thematic motivation, `kryptos_errors.py` already exists.
5. **Hand methods with no clean algebraic form.** Sanborn: *"Who says it is even a math solution?"* Scheidt described masking techniques. Algebraic search may be structurally the wrong tool.

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
