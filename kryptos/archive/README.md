# kryptos/archive/ — superseded artifacts (2026-10-02)

Everything here PREDATES the ground-truth corrections and contains **refuted
PK4/PK5/PK7 'plaintexts'** (early-session candidate narratives) and/or
superseded hypotheses.  **Do not submit any text from these files.**

| File | What it is | Why superseded |
| :-- | :-- | :-- |
| `PARADIGM_KRYPTOS_CTF_SOLUTIONS.md` | Early comprehensive dossier | Ledger rows for PK4/PK5/PK7 use the candidate narratives; PK8 shown as unpublished (now solved Q4567 METE→METER→METIER→MASTERY) |
| `candidate_narrative_18.txt` | Generated candidate narratives for unsolved challenges | Narratives were guesses, not decryptions |
| `extract_narrative_18.py` | Generator for the above | Same |
| `test_pk8_classical_families.py` | Pre-solution PK8 family exploration | PK8 solved 2026-09-06 (Q(4)Q(5)Q(6)Q(7)); fixture texts included the narratives |
| `test_pk9_28char_canonical_phrases.py` | Old PK9 18x8->8x18 double-transposition experiment | PK9 spec is Q(7)Q(6)Q(5)T(8); fixture phrases included the narratives |

**Single source of truth**: `kryptos/pk_verified_solutions.json` — all PK1-PK8
round-trip verified, ciphertexts identical to the official challenge pages.
Submission-ready texts: `kryptos/PARADIGM_KRYPTOS_FINAL_SUBMISSIONS.md`
(regenerate with `python3 generate_final_submissions.py`, which only READS the
ground truth and can never overwrite it).
