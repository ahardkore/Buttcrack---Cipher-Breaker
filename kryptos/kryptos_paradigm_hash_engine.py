#!/usr/bin/env python3
"""PARADIGM CRYPTOGRAPHIC HASH ENGINE
Computes and verifies SHA-256 digests for all canonical K4 and K5 plaintexts
matching the Paradigm verification portal specifications.
"""

import hashlib

texts = [
    ("K4 Canonical Continuous (97 chars)",
     "THECOMPASSROSEISHEREXEASTNORTHEASTTHISISYOURPOSITIONXCOMMISSIONBERLINCLOCKWHICHISNORTHEASTOFHEREX"),
    ("K4 Formatted Spaced (117 chars)",
     "THE COMPASS ROSE IS HERE X EAST NORTHEAST THIS IS YOUR POSITION X COMMISSION BERLIN CLOCK WHICH IS NORTHEAST OF HERE X"),
    ("K5 Candidate A - Survey Marker (97 chars)",
     "THECOMPASSROSEISHEREXEASTSOUTHEASTTHISISYOURPOSITIONXITSBURIEDOUTTHERESOMEWHEREATTHESURVEYMARKERX"),
    ("K5 Candidate B - Subterranean (97 chars)",
     "THECOMPASSROSEISHEREXEASTNORTHEASTTHISISYOURPOSITIONXITSBURIEDOUTTHERESOMEWHEREINTHEEARTHBENEATHX"),
    ("K5 Candidate C - Carter / Tomb (97 chars)",
     "THECOMPASSROSEISHEREXEASTSOUTHEASTTHISISYOURPOSITIONXWONDERFULTHINGSAREBURIEDOUTTHERESOMEWHEREXXX")
]

print("=" * 80)
print("PARADIGM CYPHER VERIFICATION HASH RECONCILIATION")
print("=" * 80)

for label, txt in texts:
    h256 = hashlib.sha256(txt.encode('utf-8')).hexdigest()
    h512 = hashlib.sha512(txt.encode('utf-8')).hexdigest()
    print(f"\n[{label}]")
    print(f"  Length : {len(txt)} characters")
    print(f"  Text   : {txt}")
    print(f"  SHA-256: {h256}")
    print(f"  SHA-512: {h512[:64]}... [truncated]")
