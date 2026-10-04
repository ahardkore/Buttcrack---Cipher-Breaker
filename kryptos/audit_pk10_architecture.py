#!/usr/bin/env python3
"""Audit PK10 hypotheses against the published cipher specification.

This script deliberately does not score candidate plaintext.  It separates facts
implied by the public construction H(4x4) H(3x3) Q(?) T(?) from hypotheses.  In
particular, 504 = lcm(7, 8, 9) is numerology unless a three-clock layer is first
established; the published Q denotes Quagmire, not an additive sum-clock.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = ("H(4x4)", "H(3x3)", "Q(?)", "T(?)")


def ioc(text: str) -> float:
    counts = Counter(text)
    n = len(text)
    return sum(v * (v - 1) for v in counts.values()) / (n * (n - 1))


def main() -> None:
    ciphertext = json.loads((ROOT / "pk_all_ciphertexts.json").read_text())["PK10"]
    assert len(ciphertext) == 504
    assert set(ciphertext) <= set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    print("PK10 specification audit")
    print("========================")
    print(f"Published pipeline: {' -> '.join(SPEC)}")
    print(f"Ciphertext length: {len(ciphertext)}")
    print(f"Divisible by Hill block 4: {len(ciphertext) % 4 == 0} ({len(ciphertext)//4} blocks)")
    print(f"Divisible by Hill block 3: {len(ciphertext) % 3 == 0} ({len(ciphertext)//3} blocks)")
    print(f"Joint Hill alignment period: lcm(4,3)={math.lcm(4, 3)}")
    print(f"Raw IoC: {ioc(ciphertext):.5f}")

    record = (ROOT / "pk10_record_6943.txt").read_text()
    candidate = "".join(
        line.split(":", 1)[1].split(" (", 1)[0].strip()
        for line in record.splitlines()
        if line.startswith("# Row ")
    )
    # There are two row sections in the record. Select the first 12 core rows.
    candidate = candidate[:432]
    rare = sum(candidate.count(c) for c in "JQXZ")
    print("\nLegacy 7/8/9 candidate sanity check")
    print("-----------------------------------")
    print(f"Candidate core letters read: {len(candidate)}")
    print(f"Candidate core IoC: {ioc(candidate):.5f}")
    print(f"Rare J/Q/X/Z: {rare}/{len(candidate)}")
    print("Architecture match: NO")
    print("Reason: it models an additive 7/8/9 clock plus T(42), but the public")
    print("        specification requires two Hill layers, one Quagmire layer, and T(?).")
    print("Verdict: retain only as a negative search artifact; it is not a PK10 decryption.")

    print("\nConstraints for a valid future result")
    print("-------------------------------------")
    print("1. State both invertible Hill matrices and block conventions.")
    print("2. State the Quagmire alphabet/key/indicator convention and period.")
    print("3. State the transposition width, key/order, fill, and read convention.")
    print("4. Re-encrypt all 504 letters exactly.")


if __name__ == "__main__":
    main()
