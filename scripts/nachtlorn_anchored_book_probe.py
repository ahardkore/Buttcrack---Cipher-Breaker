#!/usr/bin/env python3
"""R13: eight exact clue-bound running-key addresses, no free offset search."""
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
from scripts.nachtlorn_running_book_probe import END, OPENING, scan_domains  # noqa: E402


def anchored_domains(book: bytes) -> tuple[dict, dict]:
    text = book.decode("utf-8-sig").replace("\r\n", "\n")
    if text.count(OPENING) != 1 or text.count(END) != 1:
        raise ValueError("unique pinned story boundaries required")
    start, end = text.index(OPENING), text.index(END)
    if start >= end:
        raise ValueError("story boundaries out of order")
    story = text[start:end]

    def unique(pattern):
        matches = list(re.finditer(pattern, story))
        if len(matches) != 1:
            raise ValueError("a registered passage is missing or ambiguous")
        return matches[0]

    mother = unique(r"A\s+(?P<bowl>bowl)\s+of\s+(?P<white>white)\s+china\s+had\s+stood\s+beside\s+her\s+deathbed\s+holding\s+the\s+(?P<green>green)\s+sluggish\s+bile")
    black = unique(r"cold\s+(?P<black>black)\s+marble\s+(?P<bowl>bowl)")
    mourning = unique(r"Notice\s+because\s+I[’']m\s+in\s+(?P<mourning>mourning)\s+myself")
    anchors = {
        "deathbed-bowl": mother.start("bowl"), "after-deathbed-bowl": mother.end("bowl"),
        "deathbed-white": mother.start("white"), "deathbed-green": mother.start("green"),
        "holy-water-black": black.start("black"), "holy-water-bowl": black.start("bowl"),
        "after-holy-water-bowl": black.end("bowl"), "explicit-mourning": mourning.start("mourning"),
    }
    domains = {name: re.sub(r"[^A-Za-z]", "", story[position:]).upper() for name, position in anchors.items()}
    metadata = {name: {"normalized_story_character_offset": position,
                       "context": " ".join(story[max(0, position - 50):position + 120].split())}
                for name, position in anchors.items()}
    return domains, metadata


def scan(stream: str, book: bytes) -> dict:
    domains, metadata = anchored_domains(book)
    report = scan_domains(stream, domains, hashlib.sha256(book).hexdigest())
    report.update(hypothesis="R13", anchors=metadata,
                  status="Registered eight-address running-key test; no arbitrary offset or repeated key.",
                  caution="These already-seen passages are exploratory clue anchors, not author-confirmed instructions. Only declared ASCII letter keys, start0 within each domain, signs and packet formats. Other passages, boundaries and encodings remain untested. Roundtrips are not plaintext evidence.")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path)
    parser.add_argument("--book", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.resolve() in (args.path.resolve(), args.book.resolve()):
        parser.error("output must not overwrite either input")
    raw, book = args.path.read_bytes(), args.book.read_bytes()
    rows = raw.decode("ascii").splitlines()[8:]
    if not rows or any(not re.fullmatch(r" *[A-Z]+(?: +[A-Z]+)* *", row) for row in rows):
        parser.error("expected literal original body")
    stream = "".join(c for row in rows for c in row if "A" <= c <= "Z")
    report = scan(stream, book)
    report["source_sha256"] = hashlib.sha256(raw).hexdigest()
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"anchors": len(report["anchors"]), "letter_paths": report["letter_paths"],
                      "representation_configurations": report["representation_configurations"],
                      "structured_objects": len(report["accepted_records"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
