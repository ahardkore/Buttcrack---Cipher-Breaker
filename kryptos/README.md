# Kryptos & Paradigm Kryptos Master Cryptanalytic Suite

[![CI Test Suite](https://img.shields.io/badge/Verification%20Suite-100%25%20PASS%20(12%2F12)-3fb950?style=for-the-badge&logo=checkmarx)](test_full_suite_reproducibility.py)
[![Manuscript](https://img.shields.io/badge/Book%20Manuscript-8%20Chapters%20Complete-d97736?style=for-the-badge&logo=gitbook)](THE_KRYPTOS_DECRYPTION_MANUSCRIPT.md)
[![Web App](https://img.shields.io/badge/Web%20App-Interactive%20Suite-58a6ff?style=for-the-badge&logo=html5)](../kryptos-app/)
[![License: MIT](https://img.shields.io/badge/License-MIT-gold.svg?style=for-the-badge)](LICENSE)

An exhaustive, publication-grade cryptanalytic research repository, mathematical proof ledger, interactive web application, and full book manuscript investigating **Jim Sanborn's CIA Kryptos sculpture (K1–K4)** and **Dan Robinson's Paradigm Kryptos suite (PK1–PK10)**.

> **⚠ Status update (2026-10-03)**: PK1–PK10 reproduce their official
> ciphertexts exactly. PK9 is independently reproduced by
> `verify_pk9_solution.py` using `Q3(CLEPSYDRA) → Spiral(12) → T(BEAMWORK)`;
> its plaintext and digest are recorded in `pk_verified_solutions.json`. The
> public-solve evidence and earlier superseded candidates remain preserved in
> `PK9_OFFICIAL_SOLVE_RESEARCH_2026_10_03.md`.

---

## 🏛️ Executive Cryptanalytic Deliverables

| Deliverable | Description | Location |
| :--- | :--- | :--- |
| **Complete Book Manuscript** | 8 detailed chapters detailing the history, mathematics, and decipherment of K1–K4 and PK1–PK10. | [`THE_KRYPTOS_DECRYPTION_MANUSCRIPT.md`](THE_KRYPTOS_DECRYPTION_MANUSCRIPT.md) |
| **Executive Cryptanalytic Brief** | Rapid-recall strategic brief on final cryptanalytic verdicts and historical frontier guidance. | [`EXECUTIVE_CRYPTANALYTIC_BRIEF.md`](EXECUTIVE_CRYPTANALYTIC_BRIEF.md) |
| **Master Solutions Dossier** | Formal mathematical proofs, substitution alphabets, and verbatim plaintexts. | [`PARADIGM_KRYPTOS_MASTER_SOLUTIONS.md`](PARADIGM_KRYPTOS_MASTER_SOLUTIONS.md) |
| **Workspace Catalog & Hub** | Master index of all project assets, ciphers, and one-line verification commands. | [`WORKSPACE_CATALOG.md`](WORKSPACE_CATALOG.md) |
| **Forensic Cryptanalytic Audit** | 62 KB exhaustive audit detailing all algorithms, empirical runs, and theorems for PK9 and PK10. | [`CRYPTANALYTIC_AUDIT_PK9_PK10.md`](CRYPTANALYTIC_AUDIT_PK9_PK10.md) |
| **Master Submission Manifest** | Structured JSON database of all ciphers, parameters, plaintexts, and SHA256 checksums. | [`pk_submission_manifest.json`](pk_submission_manifest.json) |
| **Verified Solutions Database** | Machine-readable database of independently verified solutions for PK1–PK10. | [`pk_verified_solutions.json`](pk_verified_solutions.json) |
| **Interactive Web Application** | Standalone browser-based cipher explorer, architecture visualizer, book reader, and live decryptor. | [`kryptos-app/`](../kryptos-app/) |

---

## 🔬 Current Verification Record

### 1. Canonical status

**PK1–PK10 are independently verified by exact round trips.** The canonical machine-readable records are `pk_submission_manifest.json` and `pk_verified_solutions.json`. Historical PK9 readings and the former PK10 triptych remain explicitly labelled archival reports.

### 2. PK9 exact construction ($N = 144$)

PK9 is `Q3(CLEPSYDRA) → Spiral(12) → T(BEAMWORK)`. The normalized plaintext is `ISPENTTHEPASTMONTHWITHTHENEEDLEANDKNOTANDATLASTPELLEGRINSFINALMESSAGEHASBEENREVEALEDTOMEIWILLNOWSEALITFORYOUUNDEREVERYCIPHERIUSEDINTHISTESTAMENT`, with SHA-256 `c8e1b8907795acf780cbab42ec23191051dfb2fdccbfb1adbe875fe8dc03f1d8`. `verify_pk9_solution.py` reproduces all 144 ciphertext characters in both directions. The construction was independently reimplemented from the public TTFH/KRYPTOS reference; see `PK9_OFFICIAL_SOLVE_RESEARCH_2026_10_03.md` for provenance and the earlier rejected candidates.

### 3. PK10 exact cumulative construction ($N = 504$)

PK10 is verified by `verify_pk10_solution.py` with an exact 504/504 encode/decode round trip. Its forward pipeline is:

```text
Q3(PROVENANCE) → T(MARGINS) → Q3(ORDINATE) → Q3(PENTIMENTO)
→ T(UNDERLAY) → Q3(OCHRE) → Q3(VERDIGRIS) → T(TWOYEARS)
→ Q3(PK4 normalized plaintext) → T(HANDIWORK) → T(SMITHWORK)
→ Q3(PORTAL) → Q3(ANNEAL) → H3(ALCHEMIST)
→ Q3(METE) → Q3(METER) → Q3(METIER) → Q3(MASTERY)
→ Q3(CLEPSYDRA) → Spiral(12) → T(BEAMWORK)
```

The normalized plaintext begins `IHAVENOTREADTHESTRAND`, ends `ANDILEAVETHEKNOTTOYOU`, and has SHA-256 `a2db145f258ec21fbeab7afb4031e624d3184b93a3eb834d54026ba9b792e1d9`. Earlier 7/8/9-clock and 12×42 candidates are superseded research artifacts.

---

## ⚡ Reproducibility commands

```bash
python3 verify_pk9_solution.py
python3 verify_pk10_solution.py
python3 audit_all_deliverables_crosscheck.py
```

The first two commands check the PK9 and PK10 constructions in both directions. The final command cross-checks the canonical manifests, exact ciphertexts, and solution digests for PK1–PK10.

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

This repository includes a preconfigured GitHub Actions workflow in `../.github/workflows/deploy-site.yml`. When pushed to GitHub:
1. Navigate to your repository **Settings** > **Pages**.
2. Select **GitHub Actions** as the build source.
3. The interactive web application will automatically be published to `https://<USERNAME>.github.io/<REPO-NAME>/`.

---

## 📄 License
MIT License. Cryptanalytic research and open reproduction tools.
