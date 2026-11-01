#!/usr/bin/env python3
"""Historical pre-reset fragment audit; not the active investigation tool.

Use nachtlorn_reset_audit.py for the current facts-only
baseline. This legacy code is retained unchanged below for historical replay.

The author's reported construction/interpretation layers are not assumed to be
successive ciphers. This read-only audit separates source facts from proposed
key readings and short, unconfirmed candidate fragments. No source edits or
spelling corrections are made.
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.indent_seed_check import check_indent_seed  # noqa: E402
from scripts.seed_pad_probe import probe_pad  # noqa: E402

BODY_ROW = re.compile(r" *[A-Z]+(?: +[A-Z]+)* *")
JOYCE_ROSTER = (
    "BLOOM", "LEOPOLD", "MOLLY", "STEPHEN", "DEDALUS", "MULLIGAN", "HAINES",
    "DEASY", "DIGNAM", "BOYLAN", "MILLY", "LENEHAN", "BLAZES",
)


def given_taken_key(acrostic: str) -> str:
    """Hypothesis: give one to the third initial, take one from the fourth."""
    if not re.fullmatch(r"[A-Z]{5}", acrostic):
        raise ValueError("the proposed reading requires five uppercase ASCII initials")
    key = list(acrostic)
    key[2] = chr(65 + (ord(key[2]) - 65 + 1) % 26)
    key[3] = chr(65 + (ord(key[3]) - 65 - 1) % 26)
    return "".join(key)


def vigenere(stream: str, key: str, *, encrypt: bool = False) -> str:
    """Literal A=0 Vigenere over the entire supplied letter stream."""
    if not re.fullmatch(r"[A-Z]+", stream) or not re.fullmatch(r"[A-Z]+", key):
        raise ValueError("stream and key must be uppercase ASCII letters")
    sign = 1 if encrypt else -1
    return "".join(chr(65 + (ord(c) - 65 + sign * (ord(key[i % len(key)]) - 65)) % 26)
                   for i, c in enumerate(stream))


def audit(raw: bytes) -> dict:
    """Extract facts from a transcript with the original eight-line preamble."""
    text = raw.decode("ascii")
    lines = text.splitlines()
    if len(lines) < 9 or any(not re.match(r"[A-Za-z]", line) for line in lines[:5]):
        raise ValueError("expected five poem lines and a ciphertext body starting on line 9")
    body = lines[8:]
    if not body or any(not BODY_ROW.fullmatch(line) for line in body):
        raise ValueError("body must contain only uppercase ciphertext rows and ASCII spaces")
    rows = ["".join(c for c in line if "A" <= c <= "Z") for line in body]
    stream = "".join(rows)
    starts, offset = [], 0
    for row in rows:
        starts.append(offset)
        offset += len(row)
    acrostic = "".join(line[0].upper() for line in lines[:5])
    proposed = given_taken_key(acrostic)
    indentation = check_indent_seed(body, 4300)
    fragments, roster_hits, roundtrips = [], [], []
    for key in dict.fromkeys((acrostic, proposed, "BLNPM")):
        plain = vigenere(stream, key)
        roundtrips.append({"key": key, "exact_source_letter_roundtrip":
                           vigenere(plain, key, encrypt=True) == stream})
        for word in ("FRODO", "TRACT"):
            start = 0
            while (position := plain.find(word, start)) >= 0:
                row = bisect.bisect_right(starts, position) - 1
                local = position - starts[row]
                within_row = local + len(word) <= len(rows[row])
                columns = [i + 1 for i, c in enumerate(body[row]) if "A" <= c <= "Z"]
                fragments.append({
                    "decoded_literal": word, "key": key, "letter_offset": position,
                    "body_row": row + 1, "source_line": row + 9,
                    "group": local // 5 + 1 if local % 5 == 0 and within_row else None,
                    "source_columns_one_based": [columns[local], columns[local + len(word) - 1]]
                    if within_row else None,
                    "source_columns_zero_based": [columns[local] - 1, columns[local + len(word) - 1] - 1]
                    if within_row else None,
                    "ciphertext": stream[position:position + len(word)],
                    "context20": plain[max(0, position - 3):position + 17],
                    "status": "Literal unedited fragment; no unique selector or solution established.",
                })
                start = position + 1
        for name in JOYCE_ROSTER:
            start = 0
            while (position := plain.find(name, start)) >= 0:
                roster_hits.append({"key": key, "name": name, "letter_offset": position})
                start = position + 1
    native_fragment = None
    if len(stream) >= 2035:
        native_fragment = {
            "seed": 4300, "raw_word_offset": 653, "letter_offset": 2021,
            "ciphertext": stream[2021:2035],
            "decoded_literal": probe_pad(stream, 4300, 653, 2021, 14),
            "status": "Post-discovery parameters; offset653 unexplained; no spelling repair applied.",
        }
    return {
        "status": "Unresolved. This is a clue audit, not a recovered construction or answer.",
        "source_sha256": hashlib.sha256(raw).hexdigest(), "source_bytes": len(raw),
        "body_rows": len(rows), "body_letters": len(stream),
        "poem_lines": lines[:5], "acrostic": acrostic,
        "proposed_given_taken_key": {
            "key": proposed, "changed_poem_lines": [3, 4],
            "operations": ["+1", "-1"],
            "status": "Line-order hypothesis, not an author's confirmed cipher key.",
        },
        "indentation": {key: indentation[key] for key in
                        ("seed", "algorithm", "rows", "matches", "exact_match", "mismatches", "caution")},
        "literal_fragments": fragments, "roundtrips": roundtrips,
        "finite_joyce_roster": list(JOYCE_ROSTER), "joyce_roster_hits": roster_hits,
        "roster_caution": "Only the listed names and phase-zero keys; not a literary corpus search or significance test.",
        "native_fragment": native_fragment,
        "interpretation_gap": "No rule yet establishes the recovered population or selects its outlier uniquely.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path, nargs="?",
                        default=ROOT / "docs/data/nachtlorn-transcript.txt")
    args = parser.parse_args(argv)
    try:
        report = audit(args.path.read_bytes())
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
