#!/usr/bin/env python3
"""Read-only probe of an explicitly supplied MT high-five-bit/mod26 pad hypothesis.

This is NOT native random.choice/randrange(26): exactly one 32-bit MT word is
consumed per letter and its top five bits are reduced modulo26, which is biased.
A successful command only computes the requested candidate; it does not verify
plaintext, discover the parameters, or silently apply spelling corrections.
Optional source edits must be explicit and are labeled hypothetical.
"""
from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

UPPERCASE_ROW = re.compile(r" *[A-Z]+(?: +[A-Z]+)* *")
OPERATIONS = ("add", "subtract", "reverse-subtract")


def probe_pad(
    stream: str,
    seed: int,
    word_offset: int,
    letter_offset: int,
    length: int,
    operation: str = "add",
) -> str:
    """Transform one literal uppercase-letter window under supplied parameters.

    Offsets are zero-based. ``word_offset`` precedes the whole letter stream;
    the first requested pad word is therefore ``word_offset + letter_offset``.
    The local RNG leaves the caller's global random state unchanged.
    """
    if not re.fullmatch(r"[A-Z]+", stream):
        raise ValueError("stream must contain only uppercase ASCII letters")
    if word_offset < 0 or letter_offset < 0:
        raise ValueError("offsets must be nonnegative")
    if length < 1:
        raise ValueError("length must be at least 1")
    if letter_offset + length > len(stream):
        raise ValueError("requested window extends beyond the letter stream")
    if operation not in OPERATIONS:
        raise ValueError("unknown operation")
    rng = random.Random(seed)
    for _ in range(word_offset + letter_offset):
        rng.getrandbits(32)
    output = []
    for char in stream[letter_offset:letter_offset + length]:
        pad = (rng.getrandbits(32) >> 27) % 26
        cipher = ord(char) - 65
        if operation == "add":
            value = cipher + pad
        elif operation == "subtract":
            value = cipher - pad
        else:
            value = pad - cipher
        output.append(chr(65 + value % 26))
    return "".join(output)


def restore_terminal_i(stream: str, insertion_boundary: int, letter: str) -> str:
    """Return an explicitly hypothetical source, deleting only the terminal I.

    Restore one supplied letter at a zero-based boundary of the remaining
    stream. The result has the original length. This computes a hypothesis,
    not a verified correction; no file or caller state is changed.
    """
    if not re.fullmatch(r"[A-Z]+", stream) or not stream.endswith("I"):
        raise ValueError("source-edit hypothesis requires an uppercase stream ending in I")
    if not re.fullmatch(r"[A-Z]", letter):
        raise ValueError("restored letter must be one uppercase ASCII letter")
    if not 0 <= insertion_boundary <= len(stream) - 1:
        raise ValueError("restoration boundary is outside the shortened stream")
    return stream[:insertion_boundary] + letter + stream[insertion_boundary:-1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path, help="unaltered UTF-8 ciphertext transcript")
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--word-offset", required=True, type=int,
                        help="raw MT words before the complete letter stream, zero-based")
    parser.add_argument("--letter-offset", type=int, default=0,
                        help="requested window's zero-based letter offset")
    parser.add_argument("--length", required=True, type=int)
    parser.add_argument("--operation", choices=OPERATIONS, default="add")
    parser.add_argument("--body-start", type=int, metavar="LINE",
                        help="first body line, one-based; otherwise select grouped uppercase rows")
    parser.add_argument("--restore-at", type=int, metavar="BOUNDARY",
                        help="explicit hypothesis: delete final I, restore a letter here")
    parser.add_argument("--restore-letter", metavar="LETTER",
                        help="one uppercase source letter; requires --restore-at")
    args = parser.parse_args(argv)
    if (args.restore_at is None) != (args.restore_letter is None):
        parser.error("--restore-at and --restore-letter must be supplied together")
    if args.restore_at is not None:
        if args.restore_at < 0:
            parser.error("--restore-at must be nonnegative")
        if not re.fullmatch(r"[A-Z]", args.restore_letter):
            parser.error("--restore-letter must be one uppercase ASCII letter")
    if args.word_offset < 0 or args.letter_offset < 0:
        parser.error("offsets must be nonnegative")
    if args.length < 1:
        parser.error("--length must be at least 1")
    if args.body_start is not None and args.body_start < 1:
        parser.error("--body-start must be at least 1")
    try:
        lines = args.path.read_text(encoding="utf-8").splitlines()
        if args.body_start is None:
            # Avoid counting a one-word uppercase heading (e.g. BLOOM).
            # Use --body-start when single-group rows are part of the body.
            body = [line for line in lines
                    if UPPERCASE_ROW.fullmatch(line) and len(line.split()) > 1]
        else:
            body = lines[args.body_start - 1:]
            if any(not UPPERCASE_ROW.fullmatch(line) for line in body):
                raise ValueError("explicit body contains a non-uppercase ciphertext row")
        stream = "".join(char for line in body for char in line if "A" <= char <= "Z")
        original_stream = stream
        if args.restore_at is not None:
            stream = restore_terminal_i(stream, args.restore_at, args.restore_letter)
        decoded = probe_pad(stream, args.seed, args.word_offset, args.letter_offset,
                            args.length, args.operation)
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))
    report = {
        "seed": args.seed,
        "model": "one MT word per letter; top five bits modulo26",
        "operation": args.operation,
        "word_offset_before_stream": args.word_offset,
        "letter_offset": args.letter_offset,
        "first_requested_raw_word_index": args.word_offset + args.letter_offset,
        "length": args.length,
        "ciphertext_window": stream[args.letter_offset:args.letter_offset + args.length],
        "decoded_candidate": decoded,
        "caution": "Supplied-parameter hypothesis only; no plaintext verification or spelling repair.",
    }
    if args.restore_at is not None:
        report["original_ciphertext_window"] = original_stream[
            args.letter_offset:args.letter_offset + args.length
        ]
        report["hypothetical_source_edit"] = {
            "removed_terminal_I_index": len(original_stream) - 1,
            "restoration_boundary": args.restore_at,
            "restored_source_letter": args.restore_letter,
            "noop": stream == original_stream,
        }
        report["caution"] = (
            "Explicit source-edit hypothesis; input file unchanged. "
            "No plaintext verification or additional spelling repair."
        )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
