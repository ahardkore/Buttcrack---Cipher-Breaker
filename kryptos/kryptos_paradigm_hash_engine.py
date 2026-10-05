#!/usr/bin/env python3
"""PARADIGM CRYPTOGRAPHIC HASH ENGINE

Computes SHA-256/512 digests for our CANDIDATE K4 and K5 plaintexts.

IMPORTANT: these are hashes of our own unverified candidate strings. They are
self-consistent by construction and prove nothing about correctness. Paradigm's
committed hash of Sanborn's authenticated plaintext is secret, so a digest
computed here cannot be compared against it -- the only test is submitting the
string to the portal. See K4_CLAIM_STATUS_AUDIT_2026-10-05.md and
verify_k4_claim.py.
"""

import hashlib

texts = [
    ("K4 Canonical Continuous (97 chars)",
     "THECOMPASSROSEISHEREXEASTNORTHEASTTHISISYOURPOSITIONXCOMMISSIONBERLINCLOCKWHICHISNORTHEASTOFHEREX"),
    ("K4 Formatted Spaced (118 chars)",
     "THE COMPASS ROSE IS HERE X EAST NORTHEAST THIS IS YOUR POSITION X COMMISSION BERLIN CLOCK WHICH IS NORTHEAST OF HERE X"),
    ("K5 Candidate A - Survey Marker (97 chars)",
     "THECOMPASSROSEISHEREXEASTSOUTHEASTTHISISYOURPOSITIONXITSBURIEDOUTTHERESOMEWHEREATTHESURVEYMARKERX"),
    ("K5 Candidate B - Subterranean (97 chars)",
     "THECOMPASSROSEISHEREXEASTNORTHEASTTHISISYOURPOSITIONXITSBURIEDOUTTHERESOMEWHEREINTHEEARTHBENEATHX"),
    ("K5 Candidate C - Carter / Tomb (97 chars)",
     "THECOMPASSROSEISHEREXEASTSOUTHEASTTHISISYOURPOSITIONXWONDERFULTHINGSAREBURIEDOUTTHERESOMEWHEREXXX")
]

print("=" * 80)
print("PARADIGM CANDIDATE-STRING HASH LEDGER (unverified candidates)")
print("=" * 80)

for label, txt in texts:
    h256 = hashlib.sha256(txt.encode('utf-8')).hexdigest()
    h512 = hashlib.sha512(txt.encode('utf-8')).hexdigest()
    print(f"\n[{label}]")
    print(f"  Length : {len(txt)} characters")
    print(f"  Text   : {txt}")
    print(f"  SHA-256: {h256}")
    print(f"  SHA-512: {h512[:64]}... [truncated]")
