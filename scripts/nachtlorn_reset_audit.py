#!/usr/bin/env python3
"""Facts-only Nachtlorn audit for the reset investigation.

No dictionary, guessed answer, proposed cipher key, book roster, English scorer,
or earlier fragment search is imported. The layout model reuses the literal
body letters; an exact reconstruction is not decryption or a recovered solution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from collections import Counter
from pathlib import Path

BODY_ROW = re.compile(rb" *[A-Z]+(?: +[A-Z]+)* *")


def format_body(stream: str, *, seed: int = 4300, row_letters: int = 60,
                group_letters: int = 5, indent_choices: int = 8) -> bytes:
    """Forward layout model, without padding, deletion or letter transforms."""
    if not re.fullmatch(r"[A-Z]*", stream):
        raise ValueError("literal uppercase ASCII letters required")
    if min(row_letters, group_letters, indent_choices) < 1:
        raise ValueError("format dimensions must be positive")
    rng = random.Random(seed)
    rows = []
    for start in range(0, len(stream), row_letters):
        row = stream[start:start + row_letters]
        groups = " ".join(row[j:j + group_letters] for j in range(0, len(row), group_letters))
        rows.append(" " * rng.randrange(indent_choices) + groups + "\n")
    return "".join(rows).encode("ascii")


def line_content(line: bytes) -> bytes:
    if line.endswith(b"\r\n"):
        return line[:-2]
    if line.endswith((b"\n", b"\r")):
        return line[:-1]
    return line


def first_mismatch(a: bytes, b: bytes) -> int | None:
    if a == b:
        return None
    return next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))


def audit(raw: bytes) -> dict:
    raw.decode("ascii")
    lines = raw.splitlines(keepends=True)
    if len(lines) < 9:
        raise ValueError("expected the original eight-line preamble and a body")
    header, body_raw = b"".join(lines[:8]), b"".join(lines[8:])
    poem = [line_content(line).decode("ascii") for line in lines[:5]]
    if any(not line or not line[0].isalpha() for line in poem):
        raise ValueError("five literal poem lines required")
    rows = [line_content(line) for line in lines[8:]]
    if any(not BODY_ROW.fullmatch(row) for row in rows):
        raise ValueError("body rows may contain only uppercase ASCII letters and spaces")
    row_letters = [bytes(c for c in row if 65 <= c <= 90) for row in rows]
    stream = b"".join(row_letters).decode("ascii")
    reconstructed = format_body(stream)
    indents = [len(row) - len(row.lstrip(b" ")) for row in rows]
    tokens = [token for row in rows for token in row.split()]
    last_group = tokens[-1].decode("ascii")
    return {
        "status": "facts-only; no recovered answer or algorithm assignment",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_bytes": len(raw),
        "poem": {"literal_lines": poem, "literal_initials": "".join(line[0] for line in poem),
                 "uppercase_initials": "".join(line[0].upper() for line in poem)},
        "instruction": line_content(lines[6]).decode("ascii"),
        "body": {"rows": len(rows), "letters": len(stream), "printed_groups": len(tokens),
                 "row_letter_counts": {str(k): v for k, v in sorted(Counter(map(len, row_letters)).items())},
                 "group_width_counts": {str(k): v for k, v in sorted(Counter(map(len, tokens)).items())},
                 "indent_counts": {str(k): v for k, v in sorted(Counter(indents).items())},
                 "last_printed_group": last_group,
                 "last_group_is_incomplete_at_width5": len(last_group) != 5,
                 "letter_sha256": hashlib.sha256(stream.encode("ascii")).hexdigest()},
        "forward_layout": {
            "model": "layout-only-v1", "seed": 4300, "row_letters": 60,
            "group_letters": 5, "indent_choices": 8, "line_ending": "LF",
            "exact_body_reconstruction": reconstructed == body_raw,
            "exact_file_with_literal_preamble": header + reconstructed == raw,
            "first_body_mismatch_byte": first_mismatch(reconstructed, body_raw),
            "reconstructed_body_sha256": hashlib.sha256(reconstructed).hexdigest(),
            "source_body_sha256": hashlib.sha256(body_raw).hexdigest(),
            "body_letters_reused_verbatim": True,
            "letters_added_or_removed": 0,
            "scope": "Whitespace/line wrapping only. Not the letter generator, encryption, unique seed, or author-confirmed recipe."},
        "interpretation_limits": [
            "The acrostic does not assign an algorithm or confirm a password.",
            "A layout-generator fit does not establish a book reference or a body generator.",
            "An incomplete final group follows from the supplied length under this formatter; a separate marker role is unconfirmed.",
            "Exact layout does not rule out intentional alignment or letter-dependent visual extraction.",
            "No population, final outlier, or English answer is selected by this audit."],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.output and args.output.resolve() == args.path.resolve():
        parser.error("output must not overwrite source")
    try:
        report = audit(args.path.read_bytes())
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))
    serialized = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(serialized)
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
