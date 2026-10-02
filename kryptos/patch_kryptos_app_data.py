#!/usr/bin/env python3
"""Patch the hand-maintained kryptos-app/data.js with the verified
PK4/PK5/PK7 records (and repair their corrupted repeated ciphertext fields)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT.parent / "kryptos-app" / "data.js"
CTS = json.loads((ROOT / "pk_all_ciphertexts.json").read_text())
SOL = json.loads((ROOT / "pk_verified_solutions.json").read_text())

ENTRIES = {
    "PK4": {
        "title": "PK4 — Two Years In",
        "mechanism": "Columnar Transposition T(8) + Quagmire III Q(5) + Q(9)",
        "key": "UNDERLAY + OCHRE + VERDIGRIS",
        "notes": "The needle's trail reaches the Whitesmith's Alpine workshop; the search moves to a stone barn.",
    },
    "PK5": {
        "title": "PK5 — Fourteen Days in the Barn",
        "mechanism": "Columnar Transposition T(8) + Quagmire III Q(224)",
        "key": "TWOYEARS (T8) + the entire PK4 plaintext (Q224)",
        "notes": "Fourteen days of bale-lifting end with the needle pricking a finger; the Whitesmith opens the inner door.",
    },
    "PK7": {
        "title": "PK7 — Three Weeks In",
        "mechanism": "Quagmire III Q(6) + Hill Cipher 3x3 (KRYPTOS alphabet)",
        "key": "ANNEAL (Q6) + ALCHEMIST (Hill 3x3)",
        "notes": "Rise before the sun; purify the metal and draw the wire. The apprentice accepts this is not his calling.",
    },
}

text = APP.read_text()
for pk, fields in ENTRIES.items():
    # locate the entry block
    m = re.search(rf"(  {pk}: \{{\n)(.*?)(\n  \}},)", text, re.S)
    if not m:
        raise SystemExit(f"{pk} block not found in data.js")
    block = m.group(2)
    # fix ciphertext / plaintext / dynamic fields
    fixes = {
        "title": fields["title"],
        "mechanism": fields["mechanism"],
        "key": fields["key"],
        "ciphertext": CTS[pk],
        "plaintext": SOL[pk]["plaintext"],
        "notes": fields["notes"],
    }
    for field, value in fixes.items():
        pat = rf'({field}: ")(.*?)(",?)'
        new_block, n = re.subn(pat, lambda mm: mm.group(1) + value + mm.group(3), block, count=1)
        if n != 1:
            raise SystemExit(f"{pk}.{field} not patched")
        block = new_block
    text = text[:m.start(2)] + block + text[m.end(2):]

APP.write_text(text)
print("data.js patched for", ", ".join(ENTRIES))

# verify: every PK ciphertext in data.js now matches the official one
for pk in ENTRIES:
    m = re.search(rf"  {pk}: \{{.*?ciphertext: \"([A-Z]+)\"", text, re.S)
    assert m and m.group(1) == CTS[pk], pk
    m = re.search(rf"  {pk}: \{{.*?plaintext: \"([A-Z]+)\"", text, re.S)
    assert m and m.group(1) == SOL[pk]["plaintext"], pk
print("verification pass: data.js PK4/PK5/PK7 match the verified records")
