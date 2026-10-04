#!/usr/bin/env python3
"""Master submission generator for Paradigm Kryptos (PK1-PK10).

2026-10-04 UPDATE.  PK10 is now included after an exact independent
round-trip verification.  The previous version hard-coded plaintexts for PK4,
PK5 and PK7 that were early-session candidate narratives, NOT verified
solutions, and it OVERWROTE pk_verified_solutions.json with them.  That is how
a wrong PK4 text got submitted to the site and rejected.

This version is read-only with respect to the ground truth:
  - reads pk_verified_solutions.json (single source of truth, maintained by
    verify_pk_constructions.py / apply_ground_truth_corrections.py),
  - reads pk_all_ciphertexts.json (confirmed identical to the official site),
  - regenerates pk_submission_manifest.json and
    PARADIGM_KRYPTOS_FINAL_SUBMISSIONS.md from those files only,
  - never writes pk_verified_solutions.json.

Run:  python3 generate_final_submissions.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

TITLES = {
    "PK1": "PK1 — The Accession Log",
    "PK2": "PK2 — Pellegrin's Treatise",
    "PK3": "PK3 — The Viennese Anatomist",
    "PK4": "PK4 — Two Years In (the Whitesmith)",
    "PK5": "PK5 — Fourteen Days in the Barn",
    "PK6": "PK6 — The Whitesmith's Workshop",
    "PK7": "PK7 — Three Weeks In (the Craft)",
    "PK8": "PK8 — Leaving the Whitesmith",
    "PK10": "PK10 — The Archive's Successor",
}

SOLVED = [f"PK{i}" for i in range(1, 9)] + ["PK10"]
UNSOLVED_NOTES = {
    "PK9": (
        "Q(7)Q(6)Q(5)T(8) per the published cipher spec.  Extensive exact-crib, "
        "word-wheel and order searches completed 2026-10-02, all negative; see "
        "PK9_SESSION_2026_10_02_GROUND_TRUTH_AND_SWEEPS.md."
    ),
}


def main() -> None:
    sols = json.loads((ROOT / "pk_verified_solutions.json").read_text())
    cts = json.loads((ROOT / "pk_all_ciphertexts.json").read_text())

    # sanity: every solved entry must re-encrypt (verified upstream) and be
    # internally consistent; refuse to emit anything inconsistent.
    for pk in SOLVED:
        pt, ct = sols[pk]["plaintext"], cts[pk]
        assert len(pt) == len(ct), f"{pk}: length mismatch"
        assert sols[pk].get("sha256") == hashlib.sha256(pt.encode()).hexdigest(), \
            f"{pk}: sha256 mismatch — ground truth file corrupted?"

    manifest: dict = {}
    for pk in SOLVED:
        pt, ct = sols[pk]["plaintext"], cts[pk]
        manifest[pk] = {
            "status": "SOLVED",
            "challenge_id": pk,
            "title": TITLES[pk],
            "cipher_mechanism": sols[pk]["cipher"],
            "key": sols[pk]["key"],
            "ciphertext_length": len(ct),
            "plaintext_length": len(pt),
            "ciphertext": ct,
            "plaintext": pt,
            "sha256": hashlib.sha256(pt.encode()).hexdigest(),
            "verification": (
                "Exact encode/decode round-trip in verify_pk10_solution.py; "
                "ciphertext matches the official challenge page."
                if pk == "PK10" else
                "Round-trip verified in verify_pk_constructions.py; "
                "ciphertexts match the official challenge pages."
            ),
        }
    for pk, note in UNSOLVED_NOTES.items():
        manifest[pk] = {
            "status": "UNSOLVED",
            "challenge_id": pk,
            "title": pk,
            "ciphertext_length": len(cts[pk]),
            "ciphertext": cts[pk],
            "result": note,
            "verification_requirement":
                "A proposed answer must re-encrypt to every published ciphertext character.",
        }
    (ROOT / "pk_submission_manifest.json").write_text(json.dumps(manifest, indent=2))

    # human-readable submission doc
    lines = [
        "# Paradigm Kryptos CTF — Final Submissions (regenerated "
        f"{__import__('datetime').date.today().isoformat()})",
        "",
        "> **Source of truth**: `pk_verified_solutions.json` + "
        "`pk_all_ciphertexts.json` (site-confirmed).  Every solved entry below",
        "> round-trips exactly under the PK-specific verifiers.",
        "> PK9 remains unsolved; PK10 is independently round-trip verified by",
        "> `verify_pk10_solution.py`.",
        ">",
        "> PK4 provenance: independently re-confirmed 2026-10-02 by compiling the",
        "> published solver code of @TTFH3500 (github.com/TTFH/KRYPTOS,",
        "> src/ctf/PK4.h) on Linux — encode(TWOYEARSIN...) == official ciphertext,",
        "> decode(ciphertext) == TWOYEARSIN..., keys UNDERLAY/OCHRE/VERDIGRIS.",
        "",
    ]
    for pk in SOLVED:
        s, ct = sols[pk], cts[pk]
        lines += [
            f"### {TITLES[pk]} ($N = {len(ct)}$)",
            f"- **Cipher**: {s['cipher']}",
            f"- **Key**: {s['key']}",
            f"- **Plaintext (submit this, uppercase, no spaces):**",
            "  ```text",
            f"  {s['plaintext']}",
            "  ```",
            f"- **SHA256**: `{hashlib.sha256(s['plaintext'].encode()).hexdigest()}`",
            "",
        ]
    for pk, note in UNSOLVED_NOTES.items():
        lines += [f"### {pk} — UNSOLVED", f"- {note}", ""]
    (ROOT / "PARADIGM_KRYPTOS_FINAL_SUBMISSIONS.md").write_text("\n".join(lines))

    print("Regenerated pk_submission_manifest.json and "
          "PARADIGM_KRYPTOS_FINAL_SUBMISSIONS.md from the verified ground truth.")
    print("pk_verified_solutions.json was NOT modified (read-only source).")


if __name__ == "__main__":
    main()
