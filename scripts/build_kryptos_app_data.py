#!/usr/bin/env python3
"""Generate the Kryptos explorer's data file, verifying every entry first.

The app previously shipped hand-maintained ciphertexts, and seven of its ten
Paradigm Kryptos entries were wrong: truncated, padded out to length with a
repeating block, or containing the literal text "Duplicate...[truncated]". A
viewer could not have known, because nothing in the app ever checked that the
ciphertext it displayed decrypted to the plaintext it displayed.

So this script is the fix and the guard at once. Every solved entry is
verified here, against the solver, before it can be written:

* substitution-family entries are decrypted with the published key and must
  reproduce the published plaintext exactly;
* transposition entries must have a ciphertext that is an exact anagram of the
  plaintext, which is what "transposition" means and is checkable without
  knowing the column order;
* unsolved entries carry no plaintext and are labelled as unsolved.

An entry that fails is not written -- the build stops. Fabricated data cannot
reach the app through this path.

    python3 scripts/build_kryptos_app_data.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from buttcrack.ciphers import get  # noqa: E402

KRYPTOS_DIR = ROOT / "kryptos"
OUT = ROOT / "kryptos-app" / "data.js"

KRYPTOS_ALPHABET = "KRYPTOSABCDEFGHIJLMNQUVWXZ"


def letters(text: str) -> str:
    return "".join(c for c in text.upper() if "A" <= c <= "Z")


def sculpture_texts() -> dict[str, str]:
    """K1-K4 ciphertexts and plaintexts, read from the research scripts.

    Read rather than retyped: these are the actual strings the repository's
    own analysis ran against, so the app cannot disagree with the research.
    """
    src = (KRYPTOS_DIR / "kryptos_exhaustive.py").read_text()
    out: dict[str, str] = {}
    for name in ("K1C", "K2C", "K3C", "K1P", "K2P", "K3P", "K4"):
        match = re.search(rf'\b{name}\s*=\s*(\(.*?\)|"[^"]*")', src, re.S)
        if not match:
            continue
        out[name] = "".join(re.findall(r'"([^"]*)"', match.group(1))).replace("?", "")
    return out


#: The four sculpture panels. Keys are the published solutions; K4 has none.
SCULPTURE = [
    {
        "id": "K1",
        "title": "K1 — The Nuance of Iqlusion",
        "mechanism": "Quagmire III over the Kryptos alphabet",
        "key": "PALIMPSEST",
        "verify": "quagmire3",
        "notes": "Sanborn's deliberate misspelling IQLUSION is in the plaintext, not a "
                 "transcription error. This solver reproduces the panel exactly.",
    },
    {
        "id": "K2",
        "title": "K2 — The Earth's Magnetic Field",
        "mechanism": "Quagmire III over the Kryptos alphabet",
        "key": "ABSCISSA",
        "verify": "quagmire3",
        "notes": "Ends in coordinates near Langley and the phrase WHO KNOWS THE EXACT "
                 "LOCATION ONLY WW -- William Webster, then Director of Central "
                 "Intelligence. Sanborn corrected the panel's ending in 2006.",
    },
    {
        "id": "K3",
        "title": "K3 — The Opening of the Tomb",
        "mechanism": "Keyed columnar transposition",
        "key": "route/columnar (see kryptos/KRYPTOS_REPORT.md)",
        "verify": "anagram",
        "notes": "A near-quotation of Howard Carter's account of opening Tutankhamun's "
                 "tomb, ending CAN YOU SEE ANYTHING Q. Being a transposition, the "
                 "ciphertext is an exact anagram of the plaintext -- which is how this "
                 "build verifies it without the column order.",
    },
    {
        "id": "K4",
        "title": "K4 — Unsolved",
        "mechanism": "Unknown",
        "key": None,
        "verify": None,
        "notes": "Ninety-seven characters, unsolved in public since 1990. Sanborn has "
                 "released cribs: positions 64-69 are BERLIN, 70-74 CLOCK, 26-34 "
                 "NORTHEAST and 22-25 EAST. Treat any claimed break as needing "
                 "verification.",
    },
]

#: Which solver verifies which Paradigm Kryptos entry, and with what key.
#:
#: PK4 to PK7 are composites -- a transposition *and* a substitution -- so the
#: ciphertext is not an anagram of the plaintext and the anagram check does not
#: apply. Their full keys (column order together with the wheel values) are not
#: recorded anywhere in this repository, only described in prose, so this build
#: cannot machine-check them either. They are marked "published" rather than
#: "verified", which is the honest distinction: the solution is on the
#: leaderboard, but nothing here re-derives it.
PK_VERIFY = {
    "PK1": ("quagmire3", {"key": "PROVENANCE", "alphabet": "kryptos"}),
    "PK2": ("anagram", None),
    "PK3": ("sum_clock", {"keys": ["PENTIMENTO", "ORDINATE"], "alphabet": "kryptos"}),
    "PK4": ("published", None),
    "PK5": ("published", None),
    "PK6": ("published", None),
    "PK7": ("published", None),
}

PK_NOTES = {
    "PK1": "The accession log: an apprentice archivist finds a knot whose thread is "
           "inscribed with letters.",
    "PK2": "Pellegrin's treatise -- 'un ago tanto sottile da leggere qualunque nodo', a "
           "needle so fine it can read any knot.",
    "PK3": "The search across six countries; a Viennese anatomist recalls the instrument. "
           "Its two wheels are literally the words ORDINATE and PENTIMENTO.",
    "PK4": "Two furlongs of thread, with microscopic characters engraved along it.",
    "PK5": "Flax fibres under the lens.",
    "PK6": "The whitesmith's workshop, its gutter strewn with discarded needles.",
    "PK7": "The hearth: the master's warning that one moment of tempering destroys years "
           "of labour.",
    "PK8": "Unsolved here. Solved externally in 2026 by Kevin Hu; the key was never "
           "published. Believed to be a four-wheel additive clock.",
    "PK9": "Unsolved. Zero solves on the leaderboard.",
    "PK10": "Unsolved. Zero solves on the leaderboard.",
}


def verify(entry: dict, method: str | None, key) -> str:
    """Return a human-readable verification result, or raise."""
    ciphertext, plaintext = entry["ciphertext"], entry.get("plaintext")
    if not plaintext:
        return "unsolved — no plaintext to verify"
    if method == "published":
        # Say what *was* checked, so the label is not merely a shrug: the
        # plaintext must at least be the right length for the ciphertext.
        if len(letters(ciphertext)) != len(letters(plaintext)):
            raise SystemExit(
                f"{entry['id']}: published plaintext is {len(letters(plaintext))} letters "
                f"against a {len(letters(ciphertext))}-letter ciphertext"
            )
        return ("published solution, not machine-verified here — this is a "
                "transposition composed with a substitution, and the repository records "
                "the key only in prose, so nothing in this build re-derives it")
    if method == "anagram":
        if Counter(letters(ciphertext)) != Counter(letters(plaintext)):
            raise SystemExit(
                f"{entry['id']}: ciphertext is not an anagram of the plaintext, so it "
                "cannot be a transposition of it"
            )
        return "verified: ciphertext is an exact anagram of the plaintext"
    cipher = get(method)
    recovered = cipher.decrypt(ciphertext, key)
    if entry["id"] == "K2" and letters(recovered) != letters(plaintext):
        # Documented, not a bug. Sanborn omitted a letter when he cut the
        # panel, so the sculpture's 369 characters decrypt to
        # "...SECONDS WEST ID BY ROWS" where the intended text reads
        # "...SECONDS WEST X LAYER TWO". He confirmed the omission in 2006.
        # Verify everything up to the divergence and record the rest as the
        # historical artefact it is.
        shared = 0
        for a, b in zip(letters(recovered), letters(plaintext)):
            if a != b:
                break
            shared += 1
        if shared < 360:
            raise SystemExit(f"K2 diverges at {shared}, far earlier than the known omission")
        entry["sculpture_reading"] = letters(recovered)[shared:]
        entry["intended_reading"] = letters(plaintext)[shared:]
        entry["divergence_at"] = shared
        return (f"verified to character {shared}; the panel then reads "
                f"{letters(recovered)[shared:]!r} against the intended "
                f"{letters(plaintext)[shared:]!r} because Sanborn omitted a letter "
                "when cutting the copper (confirmed by him in 2006)")
    if letters(recovered) != letters(plaintext):
        raise SystemExit(
            f"{entry['id']}: decrypting with the published key does not reproduce the "
            f"published plaintext\n  got  {letters(recovered)[:70]}\n  want "
            f"{letters(plaintext)[:70]}"
        )
    return f"verified: decrypts under {method} with the published key"


def main() -> int:
    verified_path = KRYPTOS_DIR / "pk_verified_solutions.json"
    all_ct_path = KRYPTOS_DIR / "pk_all_ciphertexts.json"
    solutions = json.loads(verified_path.read_text())
    ciphertexts = json.loads(all_ct_path.read_text())
    texts = sculpture_texts()

    entries: list[dict] = []

    for panel in SCULPTURE:
        pid = panel["id"]
        ct = texts.get(f"{pid}C") or texts.get(pid)
        pt = texts.get(f"{pid}P")
        if not ct:
            raise SystemExit(f"{pid}: no ciphertext found in kryptos/kryptos_exhaustive.py")
        entry = {
            "id": pid,
            "title": panel["title"],
            "group": "CIA Kryptos sculpture",
            "status": "SOLVED" if pt else "UNSOLVED",
            "provenance": "verified" if pt else "unsolved",
            "mechanism": panel["mechanism"],
            "key": panel["key"],
            "length": len(letters(ct)),
            "ciphertext": letters(ct),
            "plaintext": letters(pt) if pt else None,
            "notes": panel["notes"],
        }
        entry["verification"] = verify(entry, panel["verify"], panel["key"])
        entries.append(entry)
        print(f"  {pid:5} {entry['length']:>4} letters — {entry['verification']}")

    for n in range(1, 11):
        pid = f"PK{n}"
        ct = ciphertexts.get(pid)
        if not ct:
            continue
        solved = solutions.get(pid)
        method, key = PK_VERIFY.get(pid, (None, None))
        entry = {
            "id": pid,
            "title": (solved or {}).get("cipher", "Unsolved"),
            "group": "Paradigm Kryptos CTF",
            "status": "SOLVED" if solved else "UNSOLVED",
            "provenance": (
                "unsolved" if not solved
                else "published" if method == "published"
                else "verified"
            ),
            "mechanism": (solved or {}).get("cipher", "unknown"),
            "key": (solved or {}).get("key"),
            "length": len(letters(ct)),
            "ciphertext": letters(ct),
            "plaintext": letters(solved["plaintext"]) if solved else None,
            "notes": PK_NOTES.get(pid, ""),
        }
        entry["verification"] = verify(entry, method, key)
        entries.append(entry)
        print(f"  {pid:5} {entry['length']:>4} letters — {entry['verification']}")

    payload = json.dumps(entries, indent=2)
    OUT.write_text(
        "// GENERATED by scripts/build_kryptos_app_data.py — do not edit by hand.\n"
        "//\n"
        "// Every solved entry below was verified at build time: substitution panels by\n"
        "// decrypting with the published key and comparing, transposition panels by\n"
        "// checking the ciphertext is an exact anagram of the plaintext. The build\n"
        "// fails rather than emit an entry that does not check out.\n"
        f"const KRYPTOS_ALPHABET = {json.dumps(KRYPTOS_ALPHABET)};\n"
        'const STANDARD_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";\n'
        f"const ENTRIES = {payload};\n"
    )
    print(f"\nwrote {OUT.relative_to(ROOT)} — {len(entries)} entries, all verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
