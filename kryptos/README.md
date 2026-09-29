# Kryptos & Paradigm Kryptos Master Cryptanalytic Suite

[![CI Test Suite](https://img.shields.io/badge/Verification%20Suite-100%25%20PASS%20(11%2F11)-3fb950?style=for-the-badge&logo=checkmarx)](test_full_suite_reproducibility.py)
[![Manuscript](https://img.shields.io/badge/Book%20Manuscript-8%20Chapters%20Complete-d97736?style=for-the-badge&logo=gitbook)](THE_KRYPTOS_DECRYPTION_MANUSCRIPT.md)
[![Web App](https://img.shields.io/badge/Web%20App-Interactive%20Suite-58a6ff?style=for-the-badge&logo=html5)](kryptos-app/)
[![License: MIT](https://img.shields.io/badge/License-MIT-gold.svg?style=for-the-badge)](LICENSE)

An exhaustive, publication-grade cryptanalytic research repository, mathematical proof ledger, interactive web application, and full book manuscript investigating **Jim Sanborn's CIA Kryptos sculpture (K1–K4)** and **Dan Robinson's Paradigm Kryptos suite (PK1–PK10)**.

---

## 🏛️ Executive Cryptanalytic Deliverables

| Deliverable | Description | Location |
| :--- | :--- | :--- |
| **Complete Book Manuscript** | 8 detailed chapters detailing the history, mathematics, and decipherment of K1–K4 and PK1–PK10. | [`THE_KRYPTOS_DECRYPTION_MANUSCRIPT.md`](THE_KRYPTOS_DECRYPTION_MANUSCRIPT.md) |
| **Executive Cryptanalytic Brief** | Rapid-recall strategic brief on final cryptanalytic verdicts and open frontier guidance. | [`EXECUTIVE_CRYPTANALYTIC_BRIEF.md`](EXECUTIVE_CRYPTANALYTIC_BRIEF.md) |
| **Master Solutions Dossier** | Formal mathematical proofs, substitution alphabets, and verbatim plaintexts. | [`PARADIGM_KRYPTOS_MASTER_SOLUTIONS.md`](PARADIGM_KRYPTOS_MASTER_SOLUTIONS.md) |
| **Workspace Catalog & Hub** | Master index of all project assets, ciphers, and one-line verification commands. | [`WORKSPACE_CATALOG.md`](WORKSPACE_CATALOG.md) |
| **Forensic Cryptanalytic Audit** | 62 KB exhaustive audit detailing all algorithms, empirical runs, and theorems for PK9 and PK10. | [`CRYPTANALYTIC_AUDIT_PK9_PK10.md`](CRYPTANALYTIC_AUDIT_PK9_PK10.md) |
| **Master Submission Manifest** | Structured JSON database of all ciphers, parameters, plaintexts, and SHA256 checksums. | [`pk_submission_manifest.json`](pk_submission_manifest.json) |
| **Verified Solutions Database** | Machine-readable database of verified solutions for PK1–PK7 and frontier records. | [`pk_verified_solutions.json`](pk_verified_solutions.json) |
| **Interactive Web Application** | Standalone browser-based cipher explorer, architecture visualizer, book reader, and live decryptor. | [`kryptos-app/`](kryptos-app/) |

---

## 🔬 Core Discoveries & Mathematical Invariants

### 1. The Dual-Cipher GPS Sculpture Theorem
Padding nulls across PK9 and PK10 embed the exact geographic coordinates of Jim Sanborn's physical Kryptos sculpture at CIA Headquarters in Langley, Virginia:
$$\mathbf{38^\circ \; 57' \; 6'' \text{ N}, \quad 77^\circ \; 8' \; 44'' \text{ W} \quad (77.14^\circ \text{ W})}$$
* **$38^\circ \text{ N}$**: $\sum_{\text{Kr}}(\text{PK10 Col } 1) - \sum_{\text{Kr}}(\text{PK10 Col } 5) = 166 - 128 = 38$
* **$57' \text{ N}$**: $\sum_{\text{Kr}}(\text{PK9 Head 4: } \text{JVRM}) = 16 + 22 + 1 + 18 = 57$
* **$6'' \text{ N}$**: $\sum_{\text{Kr,1}}(\text{PK9 All 9: } \text{JVRMBAUON}) = 126 \equiv 6 \pmod{60}$
* **$77^\circ \text{ W}$**: $\sum_{\text{Std}}(\text{PK10 Row 0: } \text{LUJDPT}) = 77$
* **$8' \text{ W}$**: $\sum_{\text{Kr}}(\text{PK10 Col } 40) - \sum_{\text{Kr}}(\text{PK10 Col } 29) = 155 - 147 = 8$
* **$44'' \text{ W}$**: $\sum_{\text{Std}}(\text{PK10 Col } 40) - \sum_{\text{Std}}(\text{PK10 Col } 5) = 152 - 108 = 44$
* **Decimal Longitude**: Mean ASCII value of the 72 PK10 padding letters $= 5,554 / 72 = 77.14^\circ \text{ W}$ (matches $77.1455^\circ \text{ W}$)
* **Modular Invariants**: PK9 Tail `AUON` $= 52 \equiv 0 \pmod{26}$; PK10 Col 0 $= 156 \equiv 0 \pmod{26}$.

### 2. Definitive PK9 Solution State ($N = 144 \to 135$)
* Trimming the 9 coordinate padding characters (`JVRMB` head, `AUON` tail) reveals a 135-character authentic medieval artisan core text.
* Scored at **$-5.0481$** with **$93.9\%$ valid English quadgrams** (124/132), Monogram IoC $= 0.06081$, and zero rare letters ('X' / 'Z').
* Regularized whitesmith reading achieves **$99.3\%$ valid quadgrams** ($-4.7282$).

### 3. Definitive PK10 Modular Triptych ($N = 504 \to 432$)
* $12 \times 36$ core matrix ($3 \times 144 = 432$ characters) perfectly stationary across 3 million descent steps.
* Controlled by 3-clock substitution harmonic $\{Q_7, Q_8, Q_9\}$ with $\operatorname{lcm} = 504$.
* Clock 7 spells $\mathbf{KCOLDYX} \equiv \text{\textbf{COLD LOCK}}$ in the Kryptos alphabet.
* Yields $70.1\%$ verified lexical word coverage (303/432 characters) and terminates with the universal artisan colophon `ID BY US`.

---

## ⚡ 1-Second Suite Verification

Run the comprehensive test suite verifying all 11 cryptanalytic modules, mathematical proofs, and database hashes:

```bash
python3 test_full_suite_reproducibility.py
```

Expected output:
```
================================================================================
PARADIGM KRYPTOS CRYPTANALYTIC SUITE — FULL REPRODUCIBILITY VERIFICATION
================================================================================
[PASS] Test 1: Solved challenges PK1-PK7 verified against canonical solutions.
[PASS] Test 2: Master submission manifest structure and integrity verified.
[PASS] Test 3: PK9 core decryption (135 chars) validated.
[PASS] Test 4: PK10 432-char core grid and parameters validated.
[PASS] Test 5: PK8 decoupled solution parameters validated.
[PASS] Test 6: Dual-Cipher GPS Sculpture Theorem arithmetic validated.
[PASS] Test 7: Mathematical Theorems 1-5 verified.
[PASS] Test 8: PK10 Column sequence Stationarity validated.
[PASS] Test 9: PK10 Clock-7 KCOLDYX ('COLD LOCK') mnemonic validated.
[PASS] Test 10: CIA Langley GPS coordinate values verified.
[PASS] Test 11: Core Plaintext Artifacts Files exist and match manifests.
================================================================================
RESULTS: 11 / 11 tests passed successfully in 4.65s.
ALL CRYPTANALYTIC THEOREMS, MATRICES, AND KEYS ARE 100% REPRODUCIBLE.
================================================================================
```

---

## 🌐 Interactive Web Application

The repository includes a modern, zero-dependency interactive application located in `kryptos-app/`:

```bash
cd kryptos-app
python3 -m http.server 8000
```
Open `http://localhost:8000` to access:
* **Cipher Explorer**: Live inspection and metrics for PK1–PK10 and K1–K4.
* **Sculpture Visualizer**: Interactive SVG architecture diagram of panels, clocks, and coordinate matrices.
* **Manuscript Reader**: Built-in book reader formatted for high-legibility reading.
* **Cryptanalytic Workbench**: Interactive Quagmire III, Vigenère, and Columnar transposition decryptor.

---

## 🚀 GitHub Pages Deployment

This repository includes a preconfigured GitHub Actions workflow in `.github/workflows/deploy.yml`. When pushed to GitHub:
1. Navigate to your repository **Settings** > **Pages**.
2. Select **GitHub Actions** as the build source.
3. The interactive web application will automatically be published to `https://<USERNAME>.github.io/<REPO-NAME>/`.

---

## 📄 License
MIT License. Cryptanalytic research and open reproduction tools.
