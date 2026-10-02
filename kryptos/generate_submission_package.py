#!/usr/bin/env python3
"""Submission package generator — thin wrapper (2026-10-02 rewrite).

The previous version hard-coded PK4/PK5 plaintexts that were early-session
candidate narratives, not verified solutions, and wrote them into
pk_submission_manifest.json.  It is replaced by this wrapper around
generate_final_submissions.py, which derives everything from
pk_verified_solutions.json (read-only, single source of truth).
"""
import sys

from generate_final_submissions import main

if __name__ == "__main__":
    main()
