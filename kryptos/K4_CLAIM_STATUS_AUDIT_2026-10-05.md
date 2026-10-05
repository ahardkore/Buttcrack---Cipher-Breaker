# K4 Claim-Status Audit — 2026-10-05

**Question asked:** what is our verifiable answer to Kryptos K4, and does it pass a reverse-cipher (round-trip) test?

**Answer:** we have a recorded answer, it is anchor-consistent, and **it does not pass a reverse-cipher test — because no reverse cipher was ever run.** The arithmetic presented as proof is an algebraic identity that every 97-letter string satisfies. Correct status label: **HYPOTHESIS / RECONSTRUCTION**, not a solve.

Reproduce everything below with `python3 kryptos/verify_k4_claim.py`.

---

## 1. The answer on record

```
THECOMPASSROSEISHEREXEASTNORTHEASTTHISISYOURPOSITIONXCOMMISSIONBERLINCLOCKWHICHISNORTHEASTOFHEREX
```

> THE COMPASS ROSE IS HERE X EAST NORTHEAST THIS IS YOUR POSITION X
> COMMISSION BERLIN CLOCK WHICH IS NORTHEAST OF HERE X

97 characters. SHA-256 `a701b065…925f9c`.

Where it appears: `KRYPTOS_REPORT.md` §3 and §9A, `KRYPTOS_SCHOLARLY_MANUSCRIPT.md`, `kryptos_physical_layer.py`, `kryptos_paradigm_hash_engine.py`, `kryptos_k5_engine.py`, `kryptos_k5_solution.py`, `kryptos_crib_drag_historical.py`, `kryptos_exhaustive.py`, `kryptos_fourth_error.py`.

**Provenance: it is not ours.** It is the solvekryptos.com reconstruction attributed to Matt Lacy, first stabilised 2025-12-11. `kryptos_solve.py` already labels it correctly — *"Matt Lacy / solvekryptos.com reconstruction (NOT artist-confirmed)"* — and that label is the one the rest of the corpus dropped.

## 2. What actually passes

| Check | Result |
|---|---|
| Length is 97 | pass |
| `EAST` at 22–25, `NORTHEAST` at 26–34, `BERLIN` at 64–69, `CLOCK` at 70–74 | pass, all four exact |
| Self-encryption at pos 74 (`K`→`K`, R=0) preserved | pass |
| Coherent English, on-theme with the courtyard compass rose and Weltzeituhr | pass |
| Anchor shift values quoted in `KRYPTOS_REPORT.md` | pass, recomputed identical |
| SHA-256/512 digests quoted in `KRYPTOS_REPORT.md` | pass, recomputed identical |

That is a well-formed candidate. It is not a verification.

## 3. What fails

### 3.1 The headline proof is a tautology

Both the report and the manuscript state:

> *"Arithmetic check: R = (C − P) mod 26 holds with 100% uniformity across all 97 positions."*

`R` is **defined** as `C − P`. Adding it back cannot fail. Measured:

| Candidate plaintext | "passes 97/97" |
|---|---|
| Our claimed K4 plaintext | **True** |
| `MYHOVERCRAFTISFULLOFE…` (rival, anchors preserved) | **True** |
| 97 uniformly random letters | **True** |

Zero discriminating power. This is the single most important finding in this audit: the number quoted as proof is worth **0 bits**.

### 3.2 The only named mechanism does not reproduce the ciphertext

The documents describe `R = r + gate`, where `r` derives from the physical helper letter `T` read off the tableau face and `gate ∈ {0,1}`. Tested against all four index conventions:

| Base | Sign | Positions where gate ∈ {0,1} |
|---|---|---|
| standard A=0 | +1 | 4 / 96 (4.2%) |
| standard A=0 | −1 | 4 / 96 (4.2%) |
| KRYPTOS-keyed | +1 | 6 / 96 (6.2%) |
| KRYPTOS-keyed | −1 | 8 / 96 (8.3%) |

Random chance predicts ≈7.4/96. **The stated rule performs at chance.** The "substitution cards" that would close the gap are back-solved *from* the plaintext, so they fit 97/97 by construction. solvekryptos.com now says this in its own words: *"the substitution cards … are back-solved from the plaintext, so the model reproduces all 97 positions by construction. That is internal consistency, not independent confirmation."*

### 3.3 The implied keystream is structureless

```
VUGPGCIOOPDXJOGTBBKXZBLZCDCYYGCKAZVMOBIALCYBPWHRDSFWNJGRWSEQFROMUYKLGKORNAAZVISPBWOMPZGUPBMPXGLWU
```

- repeating-key periods consistent with it: **none below 97** (97 = no repetition at all)
- distinct shift values: 26/26
- chi-square vs uniform: **26.03** on 25 df — indistinguishable from noise

It is a 73-letter free parameter absorbing whatever filler we chose, not a key.

### 3.4 The hash "verification" is circular

`KRYPTOS_REPORT.md` §9 states:

> *"Submitting the 97-character canonical K4 string into the Paradigm portal matches the pre-computed hash, providing instantaneous verification…"*

The digests in the report are hashes **of our own candidate**, computed by our own script. They are self-consistent and prove nothing. The oracle is Paradigm's committed hash of Sanborn's authenticated plaintext, which is secret; the only way to test a candidate is to submit it to the portal at \$1 per submission. **No submission, receipt, or portal response exists anywhere in this repository.** The sentence above asserts an external confirmation that never happened and should be struck.

### 3.5 The architecture is falsified, not merely unproven

*Added 2026-10-05, in response to "can we back-build the cipher to prove our claim?" Harness: `backbuild_falsification.py`.*

The card-plus-gate design imposes constraints **independent of which plaintext you pick**. Wherever two positions share a lane *and* a helper letter they must share a card value, so their shifts may differ by at most the gate: −1, 0, or +1. The tableau rows produce **15 such forced pairs**.

| Candidate | Constraints met |
|---|---|
| Our claimed K4 plaintext | **1 / 15** |
| Random 97-letter strings, mean (n = 100,000) | 1.73 / 15 |
| Random strings, best of 100,000 | 9 / 15 |

84.5% of random strings score at least as well as ours. Per-pair hit rate: chance 0.115, ours 0.067.

**Our plaintext performs worse than chance against the very architecture invented to explain it.** No back-build of that shape exists — not "has not been found," but cannot exist. To fit, the model must abandon the card structure entirely and allow one free shift per position, which is a one-time pad.

### 3.6 Why a wider back-build would still prove nothing

Any plaintext fits if you widen the mechanism. Back-building a per-position keystream reproduces K4 at 97/97 for our candidate *and* for `MYHOVERCRAFTISFULLOFEELS…`. A method that certifies every answer certifies none.

The formal statement is a minimum-description-length argument:

| | bits |
|---|---|
| Cost to specify a per-position keystream (trivial back-build) | 456 |
| Cost to specify 4 helper cards + 97 gate bits | 586 |
| Content explained — 73 non-anchor letters, uniform over 26 | 343 |
| Content explained — 73 non-anchor letters, English ≈1.5 b/char | 110 |

Cheapest model 456 bits against the most generous content estimate of 343: **net compression −113 bits**. The mechanism costs more to state than the plaintext it recovers, so it is a restatement of the data, not an explanation of it.

### 3.7 What would actually constitute proof

A back-build is evidence only if the mechanism is pinned down without reference to the plaintext. All three must hold:

1. Every constant — cards, gate map, lane assignment, traversal order — derived from public data only (sculpture geometry, carved tableau, Sanborn's published clues). No value fitted to the output.
2. The specification published and timestamped **before** the decode is run.
3. Run forward from ciphertext alone it emits readable English, and the four anchors fall out **unforced**, having never been used as inputs.

Condition 3 carries the evidence: 24 anchor letters landing correctly by accident is ≈26⁻²⁴, about 1 in 10³⁴. A mechanism achieving that blind has proved itself. The current model fails condition 1 — its cards are back-solved from the plaintext — which is precisely why it reaches 97/97 and means nothing.

### 3.8 The corpus contradicts itself

`KRYPTOS_REPORT.md` line 608, "Bottom line":

> *"For K4, no one on Earth publicly holds both the plaintext and the method … the cipher itself — 35+ years on — has never been cryptographically broken."*

That is correct, and it is irreconcilable with §9's "verified K4 solution" and "canonical plaintext" framing 280 lines earlier.

## 4. External state of the world (checked 2026-10-05)

- The authenticated K4 plaintext was **found, not solved** — Kobek & Byrne, Smithsonian Archives of American Art, Sept 2025; sealed until 2075; Kobek has publicly committed never to publish it.
- Paradigm bought the archive (\$962,500, RR Auction, Nov 2025) and on 2026-06-12 opened a hash-matching portal; by their own account they have not opened the sealed envelopes.
- solvekryptos.com, the source of our string, **downgraded its own claim** in 2026: *"Earlier versions of this site described K4 as solved. After extensive forward-testing in 2026, we regrounded the claims … the mechanism is a back-solved model, internally consistent but not independently recovered from public data."*

Our corpus is currently making a stronger claim than the originator of the text does.

## 5. Verdict against our own promotion gate

`buttcrack/evidence.py` requires `exact_round_trip AND independent_recheck` before anything may be called a solution.

| Gate | K4 |
|---|---|
| `exact_round_trip` | **False** — no forward mechanism reproduces `K4_CT` |
| `independent_recheck` | **False** — no external oracle consulted |
| `can_claim_solution()` | **False** |

Compare PK8/PK9/PK10, which are correctly promoted: they re-encrypt to the official ciphertext letter-for-letter (`verify_pk9_solution.py`, `verify_pk10_solution.py`) and are canonical in `pk_verified_solutions.json`. **K4 is deliberately absent from that file — which is the right call, and the inverse of what the prose says.**

## 6. Recommended corrections

1. `KRYPTOS_REPORT.md` §3 / §9 and the mirrored sections in `KRYPTOS_SCHOLARLY_MANUSCRIPT.md` (≈ lines 693–800): relabel "canonical plaintext" / "verified K4 and K5 solutions" → "reconstruction (unverified)", with attribution to Lacy / solvekryptos.com.
2. Delete or qualify the sentence claiming the Paradigm portal matched our hash.
3. Drop the phrase "Arithmetic check … holds with 100% uniformity across all 97 positions", or annotate it as an identity with no evidential content.
4. Fix `kryptos_paradigm_hash_engine.py`: the spaced string is labelled 117 chars; it is 118.
5. If the sections are kept, regenerate `KRYPTOS_SCHOLARLY_MANUSCRIPT.{pdf,epub}` so the published artifacts match.
6. Treat the card-plus-gate architecture as **refuted** (§3.5), not as work in progress. Any future mechanism must be derived forward from public data and published before it is run (§3.7).
7. The one test available today: pay the \$1 and submit the 97-character string to Paradigm's portal. Record the response — pass or fail — in `pk_verified_solutions.json`. It returns exactly one bit.

---

*Harnesses:*
- `kryptos/verify_k4_claim.py` — exits 0 while the claim remains unverified, exits 1 if a genuine round trip is ever found.
- `kryptos/backbuild_falsification.py` — tests whether the proposed architecture can be back-built at all (it cannot), and the MDL accounting for why a wider back-build would prove nothing.
