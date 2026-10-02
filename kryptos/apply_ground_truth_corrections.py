#!/usr/bin/env python3
"""Apply the verified PK4/PK5/PK7 corrections to every ground-truth record.

The previously recorded plaintexts for PK4, PK5 and PK7 do not encrypt to the
official ciphertexts under any convention; the constructions below (published
in the public TTFH/KRYPTOS reference and independently verified by
verify_pk_constructions.py against every official ciphertext) do.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

CORRECT = {
    "PK4": {
        "title": "PK4 — Two Years In",
        "cipher": "Columnar Transposition T(8) -> Quagmire III Q(5) -> Quagmire III Q(9)",
        "key": "UNDERLAY (T8) + OCHRE (Q5) + VERDIGRIS (Q9)",
        "plaintext": (
            "Two years in. The needle's trail led me to a craftsman named the Whitesmith."
            "On the road to his Alpine workshop I reread his perfunctory letters."
            "He met me at the gates and led me to a stone barn stacked with winter fodder."
            "One of his needles is hidden in the barn. I have begun to work."),
    },
    "PK5": {
        "title": "PK5 — Fourteen Days in the Barn",
        "cipher": "Columnar Transposition T(8) -> Quagmire III Q(224)",
        "key": "TWOYEARS (T8) + the entire PK4 plaintext (Q224)",
        "plaintext": (
            "Fourteen days in the barn. I worked in the manner of an archivist:"
            "lifting each bale onto a cloth and examining the straws in rows."
            "The Whitesmith brought food and water but no counsel."
            "This morning, I felt the needle prick my finger, so fine that it drew no blood."
            "I carried it to the Whitesmith, and he took it from me and opened the inner door."),
    },
    "PK7": {
        "title": "PK7 — Three Weeks In",
        "cipher": "Quagmire III Q(6) + Hill Cipher 3x3 (KRYPTOS alphabet)",
        "key": "ANNEAL (Q6) + ALCHEMIST (Hill 3x3)",
        "plaintext": (
            "Three weeks in. We rise before the sun, and each needle is done by noon."
            "The Whitesmith shows me his technique for purifying his metal before drawing it into a fine wire."
            "He has me repeat the same step four times, with slight variations. Still my hand falters."
            "I am patient, but I know this is not my calling. I have made peace with it and will go home soon."),
    },
}


def norm(text: str) -> str:
    return "".join(c for c in text.upper() if c.isalpha())


def update_json(path: Path, record_fields: set[str]) -> None:
    data = json.loads(path.read_text())
    changed = []
    for pk, spec in CORRECT.items():
        pt = norm(spec["plaintext"])
        if pk not in data:
            continue
        rec = data[pk]
        old_pt = rec.get("plaintext")
        if old_pt == pt:
            continue
        for field in record_fields & spec.keys():
            if field in rec:
                rec[field] = spec[field]
        rec["plaintext"] = pt
        if "plaintext_length" in rec:
            rec["plaintext_length"] = len(pt)
        if "sha256" in rec:
            rec["sha256"] = hashlib.sha256(pt.encode()).hexdigest()
        changed.append(f"{pk} ({len(pt)} chars)")
    if changed:
        path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
        print(f"{path.name}: corrected {', '.join(changed)}")
    else:
        print(f"{path.name}: already correct")


def main() -> None:
    update_json(ROOT / "pk_verified_solutions.json", {"cipher", "key"})
    update_json(ROOT / "pk_submission_manifest.json", {"cipher_mechanism", "key", "title"})

    # sanity: ciphertexts unchanged, lengths consistent
    cts = json.loads((ROOT / "pk_all_ciphertexts.json").read_text())
    for pk, spec in CORRECT.items():
        pt = norm(spec["plaintext"])
        assert len(pt) == len(cts[pk]), (pk, len(pt), len(cts[pk]))
    print("length checks pass; ciphertexts untouched")


if __name__ == "__main__":
    main()
