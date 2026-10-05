#!/usr/bin/env python3
"""KRYPTOS K4 — CLAIM VERIFICATION HARNESS (falsification-first).

This script exists to answer one question honestly:

    Does the 97-character K4 plaintext recorded in this repository pass an
    *exact reverse-cipher (round-trip) test* -- i.e. can we take the plaintext,
    push it forward through a stated mechanism, and get the sculpture's
    ciphertext back out?

The repository's own promotion gate (`buttcrack/evidence.py`) says a candidate
may only be called a solution when `exact_round_trip` AND `independent_recheck`
are both true.  This harness measures both for K4 and prints the verdict.

Run:  python3 kryptos/verify_k4_claim.py
Exit: 0 if the claim is correctly labelled (it is NOT a verified solve),
      1 if a genuine round trip is found (which would be real news).
"""

from __future__ import annotations

import hashlib
import random
import string
import sys
from collections import Counter

# ---------------------------------------------------------------------------
# Canonical inputs
# ---------------------------------------------------------------------------

#: K4 as inscribed on the sculpture (97 letters).
K4_CT = (
    "OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSO"
    "TWTQSJQSSEKZZWATJKLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR"
)

#: The plaintext this repository records for K4 (KRYPTOS_REPORT.md section 9A,
#: KRYPTOS_SCHOLARLY_MANUSCRIPT.md, kryptos_physical_layer.py, kryptos_k5_*.py).
#: Provenance: the solvekryptos.com reconstruction attributed to Matt Lacy,
#: first published 2025-12-11.  NOT artist-confirmed.
K4_CLAIMED_PT = (
    "THECOMPASSROSEISHEREXEASTNORTHEASTTHISISYOURPOSITIONX"
    "COMMISSIONBERLINCLOCKWHICHISNORTHEASTOFHEREX"
)

#: The only ground truth in public existence: four artist-confirmed anchors,
#: 24 of 97 letters, released by Sanborn between 2010 and 2020.  1-indexed.
ANCHORS = {
    "EAST": (22, 25),
    "NORTHEAST": (26, 34),
    "BERLIN": (64, 69),
    "CLOCK": (70, 74),
}

#: The "physical helper packet" read off the tableau face of the screen,
#: as asserted in kryptos_physical_layer.py.  This is the ONLY concrete
#: keystream source the repository names for K4.
HELPER_T = (
    "WXZK"
    "YXZKRYPTOSABCDEFGHIJLMNQUVWXZKR"
    "ZZKRYPTOSABCDEFGHIJLMNQUVWXZKRY"
    "_ABCDEFGHIJKLMNOPQRSTUVWXYZABCD"
)

KRYPTOS_ALPHABET = "KRYPTOSABCDEFGHIJLMNQUVWXZ"


def residuals(plaintext: str, ciphertext: str = K4_CT) -> list[int]:
    """R[i] = (C[i] - P[i]) mod 26."""
    return [(ord(c) - ord(p)) % 26 for c, p in zip(ciphertext, plaintext)]


def banner(title: str) -> None:
    print()
    print("=" * 78)
    print(f" {title}")
    print("=" * 78)


# ---------------------------------------------------------------------------
# Check 1 -- the anchors
# ---------------------------------------------------------------------------

def check_anchors() -> bool:
    banner("CHECK 1  Artist-confirmed anchors (necessary, far from sufficient)")
    ok = True
    for word, (start, end) in ANCHORS.items():
        got = K4_CLAIMED_PT[start - 1:end]
        hit = got == word
        ok &= hit
        print(f"  pos {start:>2}-{end:<2}  CT={K4_CT[start-1:end]:<10} "
              f"expected PT={word:<10} got={got:<10} {'OK' if hit else 'MISMATCH'}")
    print(f"\n  -> all four anchors land correctly: {ok}")
    print("  -> this constrains 24 of 97 letters (24.7%). The other 73 are free.")
    return ok


# ---------------------------------------------------------------------------
# Check 2 -- the "R = (C - P) mod 26 at 97/97" claim is an identity
# ---------------------------------------------------------------------------

def check_identity_is_vacuous() -> None:
    banner("CHECK 2  Is 'R = (C - P) mod 26 holds at 97/97 positions' evidence?")
    print("  The documents present this as the arithmetic proof of the solve.")
    print("  R is *defined* as C - P, so re-adding it cannot fail. Demonstration:\n")

    rival = "MYHOVERCRAFTISFULLOFEEASTNORTHEASTTHEWEASELATEMYLUNCHXXXQQQQQQQQQBERLINCLOCKZZZZZZZZZZZZZZZZZZZZZ"[:97]
    noise = "".join(random.Random(1990).choice(string.ascii_uppercase) for _ in range(97))

    for label, pt in (
        ("repo's claimed K4 plaintext", K4_CLAIMED_PT),
        ("a rival anchor-respecting string", rival),
        ("97 uniformly random letters", noise),
    ):
        r = residuals(pt)
        rebuilt = "".join(chr((ord(pt[i]) - 65 + r[i]) % 26 + 65) for i in range(97))
        print(f"  {label:<34} 'passes' 97/97: {rebuilt == K4_CT}")

    print("\n  -> The check passes for EVERY 97-letter string. It carries zero bits")
    print("     of evidence and cannot discriminate a solve from random noise.")


# ---------------------------------------------------------------------------
# Check 3 -- the only named mechanism: helper letter + one-bit gate
# ---------------------------------------------------------------------------

def check_stated_mechanism() -> bool:
    banner("CHECK 3  Stated mechanism: R = base(helper T) + gate, gate in {0,1}")
    r = residuals(K4_CLAIMED_PT)
    best = 0
    for name, table in (("standard A=0", None), ("KRYPTOS-keyed", KRYPTOS_ALPHABET)):
        for sign in (+1, -1):
            gates, skipped = [], 0
            for i in range(97):
                ch = HELPER_T[i]
                if not ch.isalpha():
                    skipped += 1
                    continue
                base = (ord(ch) - 65) if table is None else table.index(ch)
                gates.append((r[i] - sign * base) % 26)
            inset = sum(1 for g in gates if g in (0, 1))
            best = max(best, inset)
            print(f"  base={name:<14} sign={sign:+d}:  gate in {{0,1}} at "
                  f"{inset:>2}/{len(gates)} positions ({100*inset/len(gates):4.1f}%)"
                  f"   distinct gate values seen: {len(set(gates))}")
    print(f"\n  -> best case {best}/96 positions. Chance alone predicts ~7.4/96 (2/26).")
    print("  -> The declared helper-plus-gate rule does NOT generate the ciphertext.")
    print("     The 'substitution cards' that would make it work are back-solved")
    print("     FROM the plaintext, so they fit 97/97 by construction, not by derivation.")
    return best >= 90


# ---------------------------------------------------------------------------
# Check 4 -- is the implied keystream structured at all?
# ---------------------------------------------------------------------------

def check_keystream_structure() -> None:
    banner("CHECK 4  Does the implied keystream show any exploitable structure?")
    r = residuals(K4_CLAIMED_PT)
    ks = "".join(chr(65 + v) for v in r)
    print(f"  implied keystream: {ks}")

    consistent = [p for p in range(1, 97)
                  if not any(r[i] != r[i % p] for i in range(97))]
    print(f"\n  repeating-key periods consistent with the full keystream: "
          f"{consistent or 'none below 97'} (97 = no repetition at all)")

    counts = Counter(r)
    expected = 97 / 26
    chi = sum((counts.get(v, 0) - expected) ** 2 / expected for v in range(26))
    print(f"  distinct shift values used: {len(counts)}/26")
    print(f"  chi-square vs uniform: {chi:.2f} on 25 df (uniform noise ~= 25)")
    print("\n  -> The keystream is indistinguishable from random. It is a 73-letter")
    print("     free parameter absorbing whatever filler text we chose.")


# ---------------------------------------------------------------------------
# Check 5 -- the hashes
# ---------------------------------------------------------------------------

def check_hashes() -> None:
    banner("CHECK 5  The SHA-256 'verification' against the Paradigm portal")
    spaced = ("THE COMPASS ROSE IS HERE X EAST NORTHEAST THIS IS YOUR POSITION X "
              "COMMISSION BERLIN CLOCK WHICH IS NORTHEAST OF HERE X")
    quoted = {
        "continuous (97)": (K4_CLAIMED_PT,
                            "a701b065555773463b27fc46581d0a7f1be65ea2849d7f3a42f757cfca925f9c"),
        "spaced": (spaced,
                   "16972c2eb1f7154db5e88e39f0c2f89b5c70ef44438b5bbd499c71acdcdfc200"),
    }
    for label, (text, expect) in quoted.items():
        digest = hashlib.sha256(text.encode()).hexdigest()
        print(f"  {label:<18} len={len(text):>3}  sha256={digest[:32]}...  "
              f"{'matches the value in KRYPTOS_REPORT.md' if digest == expect else 'DIFFERS FROM REPORT'}")
    print(f"\n  note: the hash engine script labels the spaced string '117 chars'; "
          f"it is actually {len(spaced)}.")
    print("\n  -> These digests are hashes OF OUR OWN CANDIDATE. They are self-consistent")
    print("     and prove nothing. The oracle is Paradigm's committed hash of Sanborn's")
    print("     authenticated plaintext, which is secret. The only way to test a candidate")
    print("     is to submit it to the portal ($1/submission) and see it accepted.")
    print("     No such submission receipt exists anywhere in this repository.")


# ---------------------------------------------------------------------------

def main() -> int:
    print("KRYPTOS K4 — CLAIM VERIFICATION HARNESS")
    print(f"ciphertext ({len(K4_CT)}):  {K4_CT}")
    print(f"claimed PT ({len(K4_CLAIMED_PT)}):  {K4_CLAIMED_PT}")

    anchors_ok = check_anchors()
    check_identity_is_vacuous()
    mechanism_ok = check_stated_mechanism()
    check_keystream_structure()
    check_hashes()

    banner("VERDICT")
    print(f"  anchors satisfied .................. {anchors_ok}")
    print("  exact reverse-cipher round trip .... False  (no forward mechanism reproduces K4_CT)")
    print("  independent recheck ................ False  (no external oracle consulted)")
    print("  promotable under buttcrack/evidence.py ....... NO")
    print()
    print("  Correct status label: HYPOTHESIS / RECONSTRUCTION.")
    print("  It is anchor-consistent, thematically plausible, and unverified.")
    print("  Attribution: solvekryptos.com reconstruction (Matt Lacy, Dec 2025),")
    print("  which that site itself has since downgraded to 'internally consistent,")
    print("  not independently recovered from public data'.")

    return 1 if mechanism_ok else 0


if __name__ == "__main__":
    sys.exit(main())
