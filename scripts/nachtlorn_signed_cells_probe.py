#!/usr/bin/env python3
"""R7 signed-count-stripe preflight; a stripe is not a decoded IBLT or an answer.

The reference supplies logical fields, NOT an official binary serializer. This
checks explicitly hypothetical packed cells. No hash implementation, selected
word, extra cipher or implicit body repair is used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.nachtlorn_colour_probe import buffers  # noqa: E402
from scripts.nachtlorn_running_book_probe import OPERATIONS, transform  # noqa: E402

STRIDES = (16, 20, 24, 32, 48)
MAX_COUNT = 1_000_000
MIN_RUN = 32


def inspect_stripes(data: bytes, *, max_count: int = MAX_COUNT, min_run: int = MIN_RUN) -> dict:
    if max_count < 0 or min_run < 1:
        raise ValueError("nonnegative count bound and positive run length required")
    flags, summaries = [], []
    for order, prefix in (("little", "<"), ("big", ">")):
        parser = struct.Struct(prefix + "i")
        bounded = [abs(parser.unpack_from(data, offset)[0]) <= max_count
                   for offset in range(max(0, len(data) - 3))]
        for stride in STRIDES:
            runs, bests, ends = [0] * stride, [0] * stride, [None] * stride
            for offset, good in enumerate(bounded):
                residue = offset % stride
                runs[residue] = runs[residue] + 1 if good else 0
                if runs[residue] > bests[residue]:
                    bests[residue], ends[residue] = runs[residue], offset
            best = max(bests)
            residue = bests.index(best)
            best_end = ends[residue]
            summaries.append({"count_byteorder": order, "stride_bytes": stride, "longest_run": best,
                              "first_count_offset": best_end - (best - 1) * stride if best else None})
            for residue, run in enumerate(bests):
                if run >= min_run:
                    flags.append({"count_byteorder": order, "stride_bytes": stride,
                                  "longest_run": run, "first_count_offset": ends[residue] - (run - 1) * stride})
    return {"bytes": len(data), "summaries": summaries, "flags": flags,
            "longest_run": max((s["longest_run"] for s in summaries), default=0)}


def letter_paths(stream: str):
    if not re.fullmatch(r"[A-Z]+", stream) or len(stream) < 2:
        raise ValueError("literal uppercase source required")
    for marker in (False, True):
        if marker and not stream.endswith("I"):
            continue
        text = stream[:-1] if marker else stream
        yield {"drop_final_i": marker, "operation": "identity", "exact_letter_roundtrip": True}, text
        for key in ("GLOOM", "WLOOM"):
            repeating = (key * ((len(text) + len(key) - 1) // len(key)))[:len(text)]
            for operation in OPERATIONS:
                decoded = transform(text, repeating, operation)
                exact = (transform(decoded, repeating, operation, inverse=True)
                         + ("I" if marker else "")) == stream
                if not exact:
                    raise ValueError("letter-stage roundtrip failed")
                yield {"drop_final_i": marker, "operation": operation, "key": key,
                       "phase": 0, "exact_letter_roundtrip": exact}, decoded


def scan(stream: str) -> dict:
    paths, configurations, seen, records, flagged = [], 0, set(), [], []
    for path, text in letter_paths(stream):
        paths.append(path)
        for specification, data in buffers(text):
            configurations += 1
            digest = hashlib.sha256(data).hexdigest()
            if digest in seen:
                continue
            seen.add(digest)
            result = inspect_stripes(data)
            entry = {**path, **specification, "binary_sha256": digest,
                     "bytes": len(data), "longest_run": result["longest_run"], "flags": result["flags"]}
            records.append(entry)
            if result["flags"]:
                flagged.append(entry)
    return {"hypothesis": "R7", "source_letters": len(stream),
            "letter_sha256": hashlib.sha256(stream.encode()).hexdigest(),
            "parameters": {"count_bytes": 4, "maximum_absolute_count": MAX_COUNT,
                           "minimum_run": MIN_RUN, "strides": list(STRIDES),
                           "count_byteorders": ["little", "big"], "alignment": "all byte residues"},
            "letter_paths": paths, "representation_configurations": configurations,
            "unique_buffers": len(seen), "flagged_buffers": flagged, "buffer_summaries": records,
            "longest_run": max((r["longest_run"] for r in records), default=0),
            "status": "Preflight only: no item set, complete IBLT, or outlier is accepted by a count stripe.",
            "caution": "Logical reference fields have no reference wire format. Coverage is only registered packed count32 layouts, count bound, and byte representations. Flags require independent checksum, bucket-placement, full-peeling and forward-reconstruction checks. Negative preflight is not proof against other IBLTs or extra transformations."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.resolve() == args.path.resolve():
        parser.error("output must not overwrite the source")
    raw = args.path.read_bytes()
    rows = raw.decode("ascii").splitlines()[8:]
    if not rows or any(not re.fullmatch(r" *[A-Z]+(?: +[A-Z]+)* *", row) for row in rows):
        parser.error("expected literal original body")
    stream = "".join(c for row in rows for c in row if "A" <= c <= "Z")
    report = scan(stream)
    report["source_sha256"] = hashlib.sha256(raw).hexdigest()
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"letter_paths": len(report["letter_paths"]),
                      "representation_configurations": report["representation_configurations"],
                      "unique_buffers": report["unique_buffers"],
                      "flagged_buffers": len(report["flagged_buffers"]), "longest_run": report["longest_run"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
