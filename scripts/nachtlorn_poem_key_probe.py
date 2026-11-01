#!/usr/bin/env python3
"""R9: declared +/-1 edits of the two O initials, after a book-colour hypothesis."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.nachtlorn_colour_probe import proposal, scan  # noqa: E402


def derive(poem: list[str], replacement: str | None) -> dict:
    if (len(poem) != 5 or "".join(line[:1].upper() for line in poem) != "BLOOM"
            or poem[2:4] != ["one given.", "one taken."]
            or poem[0] != "blue at the bottom of the bowl."):
        raise ValueError("expected literal source poem")
    if replacement not in (None, "green", "white"):
        raise ValueError("only registered colour hypotheses or unchanged baseline")
    initials = list("BLOOM")
    if replacement:
        initials[0] = replacement[0].upper()
    before = "".join(initials)
    initials[2] = chr(ord(initials[2]) + 1)
    initials[3] = chr(ord(initials[3]) - 1)
    return {"replacement": replacement, "before_unit_shifts": before, "derived_key": "".join(initials),
            "operations": [{"poem_line": 3, "initial": "O", "delta": 1, "result": "P"},
                           {"poem_line": 4, "initial": "O", "delta": -1, "result": "N"}],
            "unchanged_initial_positions": [2, 5] if replacement else [1, 2, 5],
            "caution": "These are derived-key instructions under a hypothesis, not literal corrected acrostics or confirmed author directions."}


def scan_all(raw: bytes, book: bytes) -> dict:
    primary = proposal(raw, book)
    rows = raw.decode("ascii").splitlines()[8:]
    if not rows or any(not re.fullmatch(r" *[A-Z]+(?: +[A-Z]+)* *", row) for row in rows):
        raise ValueError("expected literal body")
    stream = "".join(c for row in rows for c in row if "A" <= c <= "Z")
    candidates = []
    for replacement in ("green", "white", None):
        derivation = derive(primary["original_poem"], replacement)
        candidates.append({"derivation": derivation, **scan(stream, derivation["derived_key"])})
    return {"hypothesis": "R9", "source_sha256": hashlib.sha256(raw).hexdigest(),
            "book_sha256": hashlib.sha256(book).hexdigest(), "book_passage": primary["book_passage"],
            "candidate_reports": candidates,
            "caution": "Alternative derived keys, never stacked encryptions. Historical BLPNM is a mechanical baseline, not a reason to accept old word fragments. No recovered population or outlier follows from key derivation alone."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path)
    parser.add_argument("--book", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.resolve() in (args.path.resolve(), args.book.resolve()):
        parser.error("output must not overwrite either input")
    report = scan_all(args.path.read_bytes(), args.book.read_bytes())
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps([{"key": row["key"],
                       "structured_objects": len(row["literal_key_test"]["accepted_records"]),
                       "authentication_status": row["standalone_password_test"]["status"],
                       "authentication_attempts": row["standalone_password_test"]["authentication_attempts"],
                       "valid_tags": len(row["standalone_password_test"]["accepted"])}
                      for row in report["candidate_reports"]]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
