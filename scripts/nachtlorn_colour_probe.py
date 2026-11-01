#!/usr/bin/env python3
"""R5/R6/R9/R11: explicitly registered colour/poem keys, not historical key grids."""
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
from scripts.nachtlorn_aead_probe import AES, MODES, Crypto, derive_keys, probe_packet  # noqa: E402
from scripts.nachtlorn_role_probe import decode26  # noqa: E402
from scripts.nachtlorn_running_book_probe import OPERATIONS, inspect_packet, transform  # noqa: E402


def proposal(raw: bytes, book: bytes, replacement: str = "green") -> dict:
    if replacement not in ("green", "white"):
        raise ValueError("only the registered contents/vessel colours are admitted")
    lines = raw.decode("ascii").splitlines()
    if len(lines) < 9 or lines[0] != "blue at the bottom of the bowl.":
        raise ValueError("expected original poem and body")
    if "".join(line[0].upper() for line in lines[:5]) != "BLOOM":
        raise ValueError("expected original BLOOM acrostic")
    quote = re.search(r"A bowl of white china[^.]*\.", " ".join(book.decode("utf-8-sig").split()))
    if quote is None or "green sluggish bile" not in quote.group():
        raise ValueError("expected pinned bowl passage")
    revised = [replacement + lines[0][4:], *lines[1:5]]
    return {"original_poem": lines[:5], "proposed_poem": revised,
            "derived_acrostic": "".join(line[0].upper() for line in revised),
            "book_passage": quote.group(), "content_colour": "green", "vessel_colour": "white",
            "status": "User-motivated interpretation, not a confirmed source correction."}



def reference_contexts(book: bytes) -> dict:
    text = book.decode("utf-8-sig").replace("\r\n", "\n")
    opening = text.index("Stately, plump Buck Mulligan")
    end = text.index("*** END OF THIS PROJECT GUTENBERG EBOOK ULYSSES ***")
    story = text[opening:end]
    tokens = list(re.finditer(r"[A-Za-z]+", story))
    markers = list(re.finditer(r"^\[\s*(\d+)\s*\]", story, re.M))
    colours = ("blue", "green", "white", "yellow", "black")
    records = []
    for index, match in enumerate(tokens):
        if match.group().lower() not in ("bowl", "bowls"):
            continue
        episode = 1
        for marker in markers:
            if marker.start() > match.start():
                break
            episode = int(marker.group(1))
        left, right = max(0, index - 40), min(len(tokens), index + 41)
        nearby = [{"token": tokens[j].group(), "relative_token": j - index}
                  for j in range(left, right) if tokens[j].group().lower() in colours]
        records.append({"episode": episode, "token": match.group(), "story_token_index": index,
                        "story_character_offset": match.start(), "nearby_colour_tokens": nearby,
                        "context": " ".join(story[tokens[left].start():tokens[right - 1].end()].split())})
    return {"domain": "Stately through Gutenberg END", "ascii_word_tokens": len(tokens),
            "window_tokens_each_side": 40, "colour_queries": list(colours), "bowl_token_hits": len(records),
            "records": records,
            "caution": "Exploratory context audit. Exact bowl/bowls tokens include other senses. Proximity does not establish a colour modifies a bowl; blue absence is not proof of an intentional error."}


def buffers(text: str):
    """Exactly the registered A0/A1, two byte orders, and 0..7 zero restoration."""
    for bias in (0, 1):
        big = decode26(text, bias)
        for order, minimal in (("big", big), ("little", big[::-1])):
            for zeros in range(8):
                data = b"\0" * zeros + minimal if order == "big" else minimal + b"\0" * zeros
                yield {"bias": bias, "byteorder": order, "restored_zero_bytes": zeros}, data


def scan(stream: str, key: str = "GLOOM") -> dict:
    if not re.fullmatch(r"[A-Z]+", stream) or len(stream) < 2 or key not in ("GLOOM", "WLOOM", "GLPNM", "WLPNM", "BLPNM", "BLACK", "GREEN", "WHITE"):
        raise ValueError("literal source and explicitly registered colour/poem key required")
    passwords = (key, key.lower(), key.title())
    keys = derive_keys(passwords)
    scope = ("R5" if key == "GLOOM" else "R6" if key == "WLOOM" else
             "R11" if key in ("BLACK", "GREEN", "WHITE") else "R9")
    exclusions = ("No routes, changed O initials, phase search, word targets or stacked encryption."
                  if key in ("GLOOM", "WLOOM", "BLACK", "GREEN", "WHITE") else
                  "No routes, further key edits, phase search, word targets or stacked encryption.")
    paths, representation_count, attempts, auth_representations = 0, 0, 0, 0
    structured, authenticated, roundtrips = [], [], []
    seen_auth, seen_structured, by_mode = set(), set(), {}
    for marker in (False, True):
        if marker and not stream.endswith("I"):
            continue
        text = stream[:-1] if marker else stream
        repeating = (key * ((len(text) + len(key) - 1) // len(key)))[:len(text)]
        for operation in OPERATIONS:
            decoded = transform(text, repeating, operation)
            exact = (transform(decoded, repeating, operation, inverse=True)
                     + ("I" if marker else "")) == stream
            if not exact:
                raise ValueError("letter-stage roundtrip failure")
            path = {"drop_final_i": marker, "operation": operation, "key": key, "phase": 0}
            roundtrips.append({**path, "exact_letter_roundtrip": exact})
            paths += 1
            for spec, data in buffers(decoded):
                representation_count += 1
                digest = hashlib.sha256(data).hexdigest()
                if digest in seen_structured:
                    continue
                seen_structured.add(digest)
                objects = inspect_packet(data)
                if objects:
                    structured.append({**path, **spec, "binary_sha256": digest, "objects": objects})
        # Independent alternative role: password on RAW base26, not another
        # encryption layer stacked on the repeating-key output.
        for spec, data in buffers(text):
            auth_representations += 1
            digest = hashlib.sha256(data).hexdigest()
            if digest in seen_auth:
                continue
            seen_auth.add(digest)
            if AES is None:
                continue
            result = probe_packet(data, keys)
            attempts += result["attempts"]
            for mode, count in result["by_mode"].items():
                by_mode[mode] = by_mode.get(mode, 0) + count
            for accepted in result["accepted"]:
                authenticated.append({"drop_final_i": marker, **spec,
                                      "binary_sha256": digest, **accepted})
    return {"key": key, "source_letters": len(stream), "letter_sha256": hashlib.sha256(stream.encode()).hexdigest(),
            "literal_key_test": {"letter_paths": paths, "representation_configurations": representation_count,
                                 "unique_buffers": len(seen_structured), "roundtrips": roundtrips,
                                 "accepted_records": structured},
            "standalone_password_test": {
                "status": "tested" if AES is not None else "not_run_missing_optional_dependency",
                "crypto_version": Crypto.__version__ if Crypto is not None else None,
                "password_cases": list(passwords),
                "key_specification": [{k: v for k, v in row.items() if k != "key"} for row in keys],
                "modes": [list(pair) for pair in MODES], "tag_bytes": 16, "associated_data": "empty",
                "representation_configurations": auth_representations, "unique_buffers": len(seen_auth),
                "authentication_attempts": attempts, "attempts_by_mode": by_mode, "accepted": authenticated},
            "caution": f"Only registered {scope} alternatives. {exclusions} Neither negative tests nor exact roundtrips establish the right reading."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--book", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--replacement", choices=("green", "white"), default="green")
    args = parser.parse_args(argv)
    if args.output.resolve() in (args.path.resolve(), args.book.resolve()):
        parser.error("output must not overwrite either input")
    raw, book = args.path.read_bytes(), args.book.read_bytes()
    proposed = proposal(raw, book, args.replacement)
    body = raw.decode("ascii").splitlines()[8:]
    if not body or any(not re.fullmatch(r" *[A-Z]+(?: +[A-Z]+)* *", row) for row in body):
        parser.error("expected literal original body")
    stream = "".join(c for row in body for c in row if "A" <= c <= "Z")
    report = {"hypothesis": "R5" if args.replacement == "green" else "R6", "source_sha256": hashlib.sha256(raw).hexdigest(),
              "book_sha256": hashlib.sha256(book).hexdigest(), "proposal": proposed,
              **scan(stream, proposed["derived_acrostic"])}
    if args.replacement == "white":
        report["reference_audit"] = reference_contexts(book)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"key": report["key"], "letter_paths": report["literal_key_test"]["letter_paths"],
                      "structured_objects": len(report["literal_key_test"]["accepted_records"]),
                      "authentication_status": report["standalone_password_test"]["status"],
                      "authentication_attempts": report["standalone_password_test"]["authentication_attempts"],
                      "valid_tags": len(report["standalone_password_test"]["accepted"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
