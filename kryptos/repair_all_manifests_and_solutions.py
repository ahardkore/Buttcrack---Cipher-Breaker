#!/usr/bin/env python3
"""DEPRECATED 2026-10-02 — DO NOT USE.

The previous version of this script hard-coded PK4/PK5/PK7 'plaintexts' that
were early-session candidate narratives, not verified solutions, and it
OVERWROTE pk_verified_solutions.json with them.  That is how a wrong PK4 text
was submitted to the site and rejected.

The ground truth is maintained in pk_verified_solutions.json by
verify_pk_constructions.py (all PK1-PK8 re-verified, ciphertexts match the
official challenge pages).  Regenerate downstream artifacts with
generate_final_submissions.py, which only READS the ground truth.
"""
import sys

sys.exit(
    "repair_all_manifests_and_solutions.py is deprecated and does nothing.\n"
    "  - ground truth: pk_verified_solutions.json (see verify_pk_constructions.py)\n"
    "  - regenerate manifest/docs: python3 generate_final_submissions.py"
)
