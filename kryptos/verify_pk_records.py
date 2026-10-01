#!/usr/bin/env python3
"""Check every stored Paradigm Kryptos record against its own ciphertext.

A record in ``pk_verified_solutions.json`` claims three things: a plaintext, a
cipher and a key.  This script tests the only claim that can actually be
settled mechanically -- **does the stated key turn the stated plaintext back
into the published ciphertext, character for character?** -- and reports the
measured English-ness of every candidate alongside it.

Verdicts
--------

``VERIFIED``
    The key reproduces the ciphertext exactly.  Nothing is taken on trust.

``NOT REPRODUCIBLE``
    The plaintext reads as English but the stated key does not reproduce the
    ciphertext under any convention this script knows.  That is a statement
    about the *record*, not proof that the plaintext is wrong.

``NOT ENGLISH``
    A stored candidate that the language model does not read as English.  A
    candidate may be internally consistent with the key it names and still be
    a failed attack, which is exactly the PK8 case.

Run it from anywhere::

    python3 kryptos/verify_pk_records.py [--json]

Exit status is non-zero when a record labelled SOLVED does not verify, so CI
and ``tests/test_kryptos_records.py`` can enforce it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from buttcrack.ciphers import get  # noqa: E402
from buttcrack.lang import get_model  # noqa: E402

CORPUS = ROOT / "kryptos"
KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
INDEX = {ch: i for i, ch in enumerate(KRYPTOS)}

#: Fitness at which the quadgram model calls a reading English.  Real PK
#: plaintexts measure -4.2 to -4.5; the failed candidates measure -6 and worse.
ENGLISH_FITNESS = -5.0


# --------------------------------------------------------------------------- #
# The primitives, written out so a reader can check the conventions by eye.
# --------------------------------------------------------------------------- #
def keyed_shift(text: str, shifts: list[int], sign: int) -> str:
    """Add a repeating keystream in KRYPTOS-alphabet index space."""
    return "".join(
        KRYPTOS[(INDEX[ch] + sign * shifts[i % len(shifts)]) % 26] for i, ch in enumerate(text)
    )


def quagmire3(text: str, keyword: str, sign: int) -> str:
    return keyed_shift(text, [INDEX[c] for c in keyword], sign)


def sum_clock(text: str, words: list[str], sign: int) -> str:
    """Several wheels added together, one keyed letter per wheel position."""
    wheels = [[INDEX[c] for c in word] for word in words]
    out = []
    for t, ch in enumerate(text):
        k = sum(wheel[t % len(wheel)] for wheel in wheels) % 26
        out.append(KRYPTOS[(INDEX[ch] + sign * k) % 26])
    return "".join(out)


def columnar(text: str, width: int, order: list[int]) -> str:
    """Write the text into rows of ``width`` and read the columns in ``order``."""
    rows = len(text) // width
    grid = [text[r * width : (r + 1) * width] for r in range(rows)]
    return "".join(grid[r][c] for c in order for r in range(rows))


# --------------------------------------------------------------------------- #
# One reconstruction per record.  Each returns the ciphertext it rebuilds from
# the stored plaintext, or None when the record does not state a usable key.
# --------------------------------------------------------------------------- #
def rebuild_pk1(pt: str) -> str:
    return get("quagmire3").encrypt(pt, {"key": "PROVENANCE", "alphabet": "kryptos"})


def rebuild_pk2(pt: str) -> str:
    return columnar(pt, 7, [1, 3, 4, 0, 5, 2, 6])


def rebuild_pk3(pt: str) -> str:
    return sum_clock(pt, ["PENTIMENTO", "ORDINATE"], +1)


def rebuild_pk6(pt: str) -> str:
    stage1 = columnar(pt, 9, [1, 3, 0, 4, 8, 2, 6, 7, 5])
    stage2 = columnar(stage1, 9, [4, 2, 8, 1, 6, 7, 0, 3, 5])
    return quagmire3(stage2, "PORTAL", +1)


def rebuild_pk7(pt: str) -> str:
    return get("keyed_hill").encrypt(
        pt, {"matrix": "ALCHEMIST", "key": "ANNEAL", "alphabet": "kryptos"}
    )


REBUILD = {
    "PK1": rebuild_pk1,
    "PK2": rebuild_pk2,
    "PK3": rebuild_pk3,
    "PK6": rebuild_pk6,
    "PK7": rebuild_pk7,
}

#: Records whose key is stated too loosely to rebuild, with what was tried.
UNREPRODUCIBLE = {
    "PK4": (
        "the record names only 'Dual-Clock Substitution p5 + p9, Transposition Width 8'. "
        "Every columnar convention at widths 8 and 28 was searched against the stored "
        "plaintext, with the keystream phased from either side and over both alphabets; "
        "none reproduces the ciphertext."
    ),
    "PK5": (
        "the record names only 'Quagmire III Period 17, Transposition Width 16'. No column "
        "order reproduces the ciphertext, and the stated order (transposition, then a "
        "period-17 keystream) is impossible for this plaintext whatever the transposition: "
        "no set of 17 shifts maps the ciphertext's residue classes onto the plaintext's "
        "letter multiset."
    ),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    ciphertexts = json.loads((CORPUS / "pk_all_ciphertexts.json").read_text())
    solutions = json.loads((CORPUS / "pk_verified_solutions.json").read_text())
    manifest = json.loads((CORPUS / "pk_submission_manifest.json").read_text())
    model = get_model()

    results = []
    for name in (f"PK{i}" for i in range(1, 11)):
        ciphertext = ciphertexts.get(name, "")
        record = solutions.get(name) or manifest.get(name) or {}
        plaintext = record.get("plaintext") or record.get("candidate_plaintext") or ""
        score = model.score(plaintext) if plaintext else None
        entry = {
            "id": name,
            "stored_status": record.get("status", "-"),
            "fitness": round(score.fitness, 2) if score else None,
            "words": round(score.words, 3) if score else None,
        }
        if not plaintext:
            entry["verdict"] = "NO PLAINTEXT"
            entry["detail"] = "unsolved; no plaintext stored"
        elif name in REBUILD:
            rebuilt = REBUILD[name](plaintext)
            ok = rebuilt == ciphertext
            entry["verdict"] = "VERIFIED" if ok else "KEY MISMATCH"
            entry["detail"] = (
                "stated key re-encrypts the plaintext to the published ciphertext"
                if ok
                else "the stated key does NOT reproduce the ciphertext"
            )
        elif score and score.fitness < ENGLISH_FITNESS:
            entry["verdict"] = "NOT ENGLISH"
            entry["detail"] = (
                f"stored candidate scores {score.fitness:.2f} log10/char against English's "
                f"-4.3 and {score.words:.0%} coverage in words of four letters or more; "
                "it is a failed attack, not a solution"
            )
        else:
            entry["verdict"] = "NOT REPRODUCIBLE"
            entry["detail"] = UNREPRODUCIBLE.get(name, "no key stated")
        results.append(entry)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"{'id':5} {'verdict':17} {'stored status':34} {'fitness':>8} {'words':>6}")
        print("-" * 78)
        for e in results:
            fit = f"{e['fitness']:8.2f}" if e["fitness"] is not None else " " * 8
            words = f"{e['words']:6.0%}" if e["words"] is not None else " " * 6
            print(f"{e['id']:5} {e['verdict']:17} {e['stored_status'][:33]:34} {fit} {words}")
        print()
        for e in results:
            print(f"  {e['id']}: {e['detail']}")

    # A record may only call itself SOLVED if the key reproduces the ciphertext.
    broken = [
        e for e in results
        if e["stored_status"].upper().startswith("SOLVED") and e["verdict"] != "VERIFIED"
    ]
    if broken:
        print("\nFAIL: " + ", ".join(f"{e['id']} claims SOLVED but is {e['verdict']}" for e in broken))
        return 1
    print("\nOK: every record labelled SOLVED reproduces its ciphertext from its stated key.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
