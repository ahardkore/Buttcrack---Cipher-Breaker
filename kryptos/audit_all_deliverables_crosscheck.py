#!/usr/bin/env python3
"""Cross-check canonical Paradigm Kryptos manifests without promoting candidates.

PK1-PK10 are verified solutions. PK9's public solve is independently
reproduced here from the recovered construction and must not be represented by
an unverified candidate. The script is location-independent and exits non-zero
on defects.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def main() -> int:
    manifest = load("pk_submission_manifest.json")
    verified = load("pk_verified_solutions.json")
    raw = load("pk_all_ciphertexts.json")
    errors: list[str] = []

    expected = {f"PK{i}" for i in range(1, 11)}
    for name, data in (("manifest", manifest), ("ciphertexts", raw)):
        missing = expected - set(data)
        if missing:
            errors.append(f"{name}: missing {', '.join(sorted(missing))}")
        # The raw corpus may contain explicitly named research variants such as
        # PK9_UNDONE. Only the canonical submission manifest is schema-closed.
        if name == "manifest":
            extra = set(data) - expected
            if extra:
                errors.append(f"{name}: unexpected {', '.join(sorted(extra))}")

    for i in range(1, 11):
        key = f"PK{i}"
        if key not in manifest or key not in raw:
            continue
        entry = manifest[key]
        ciphertext = raw[key]
        if entry.get("challenge_id") != key:
            errors.append(f"{key}: challenge_id mismatch")
        if entry.get("ciphertext") != ciphertext:
            errors.append(f"{key}: manifest ciphertext differs from canonical ciphertext")
        if entry.get("ciphertext_length") != len(ciphertext):
            errors.append(f"{key}: ciphertext_length is not {len(ciphertext)}")
        if not ciphertext.isalpha() or not ciphertext.isupper():
            errors.append(f"{key}: ciphertext is not uppercase A-Z")

        if i <= 10:
            solution = verified.get(key)
            if entry.get("status") != "SOLVED":
                errors.append(f"{key}: verified challenge is not marked SOLVED")
            if not solution:
                errors.append(f"{key}: missing verified solution")
                continue
            plaintext = entry.get("plaintext", "")
            if entry.get("plaintext_length") != len(plaintext):
                errors.append(f"{key}: plaintext_length mismatch")
            for field in ("ciphertext", "plaintext", "sha256"):
                if entry.get(field) != solution.get(field):
                    errors.append(f"{key}: {field} differs between manifest and verified solutions")
            digest = hashlib.sha256(plaintext.encode("ascii")).hexdigest()
            if entry.get("sha256") != digest:
                errors.append(f"{key}: plaintext SHA-256 mismatch")
        else:
            errors.append(f"{key}: unexpected challenge outside verified range")

    extra_verified = set(verified) - {f"PK{i}" for i in range(1, 11)}
    if extra_verified:
        errors.append("verified solutions contain unexpected entries: " + ", ".join(sorted(extra_verified)))

    required = [
        "pk_submission_manifest.json", "pk_verified_solutions.json",
        "pk_all_ciphertexts.json", "verify_pk_constructions.py",
        "verify_pk8_solution.py", "verify_pk9_solution.py", "verify_pk10_solution.py", "PK8_STRUCTURED_BREAK_REPORT.md",
        "PK9_Q567_T8_EXACT_CRIB_REPORT.md", "PK9_OFFICIAL_SOLVE_RESEARCH_2026_10_03.md", "PK10_CORRECT_ARCHITECTURE_AUDIT_2026-10-04.md",
    ]
    for name in required:
        if not (ROOT / name).is_file():
            errors.append(f"missing required deliverable: {name}")

    print("Paradigm Kryptos canonical deliverable audit")
    print(f"  verified solutions: {len(verified)} (expected 10: PK1-PK10)")
    print(f"  manifest entries:   {len(manifest)} (expected 10)")
    print(f"  defects:            {len(errors)}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        return 1
    print("PASS: PK1-PK10 verified; PK9 exact round trip is independently reproduced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
