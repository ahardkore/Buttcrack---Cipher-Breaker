#!/usr/bin/env python3
"""Score the solver against the Paradigm Kryptos CTF corpus.

PK1-PK7 have published solutions, so they are a *scorecard*: the plaintext is
known and either the solver reproduces it or it does not.  PK8-PK10 have no
published key here -- PK8 was solved externally and its key was never released,
PK9 and PK10 have zero solves on the leaderboard -- so for those the script
reports the best n-gram fitness reached and compares it with the records in
`kryptos/PK8-PK10.md` (PK9 -5.2493, PK10 -7.6180).
Nothing here claims a break that the plaintext does not demonstrate.

    python3 scripts/kryptos_ctf.py [--budget 60] [--only PK1,PK3]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from buttcrack import solve  # noqa: E402
from buttcrack.lang import get_model  # noqa: E402

CORPUS = ROOT / "kryptos"
#: Records from the repository's own dossier, for the unsolved three.
RECORDS = {"PK9": -5.2493, "PK10": -7.6180}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--budget", type=float, default=60.0)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--only", help="comma-separated subset, e.g. PK1,PK3")
    args = parser.parse_args()

    ciphertexts = json.loads((CORPUS / "pk_all_ciphertexts.json").read_text())
    solutions = json.loads((CORPUS / "pk_verified_solutions.json").read_text())
    wanted = args.only.split(",") if args.only else [f"PK{i}" for i in range(1, 11)]
    model = get_model()

    solved = attempted = 0
    for name in wanted:
        ciphertext = ciphertexts.get(name)
        if not ciphertext:
            continue
        attempted += 1
        started = time.time()
        report = solve(ciphertext, budget=args.budget, workers=args.workers)
        elapsed = time.time() - started
        got = "".join(c for c in report.plaintext.upper() if c.isalpha())
        truth = solutions.get(name, {}).get("plaintext")
        fitness = model.search_fitness(got) if got else float("-inf")
        if truth:
            ok = got.startswith(truth[:60])
            solved += ok
            verdict = "SOLVED" if ok else "miss  "
            extra = f"  ({solutions[name]['cipher']})"
        else:
            record = RECORDS.get(name)
            verdict = "open  "
            # Fitness is per character, so it is only comparable with a
            # published record when the reading covers the whole message.  A
            # chain that decodes 17 of 504 letters can score better than a
            # real 504-letter decryption while meaning nothing at all, and
            # reporting that as "beat the record" would be a lie.
            covered = len(got) / max(1, len(ciphertext))
            extra = f"  fitness {fitness:.4f} over {len(got)}/{len(ciphertext)} letters"
            if record:
                extra += (
                    f" vs record {record:.4f}"
                    if covered > 0.95
                    else f" (record {record:.4f} not comparable: partial reading)"
                )
            else:
                extra += " (no published key)"
        print(f"{verdict} {name:5} {elapsed:6.1f}s conf={report.confidence:.2f} {report.path}{extra}")
        if truth and not got.startswith(truth[:60]):
            print(f"       expected {truth[:56]}")
            print(f"       got      {got[:56]}")

    known = [n for n in wanted if n in solutions]
    print(f"\n{solved}/{len(known)} of the published solutions reproduced "
          f"({attempted} challenges attempted)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
