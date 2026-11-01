#!/usr/bin/env python3
"""Exact single-exception checks with arbitrary letter functions per position.

A one-hot row has one indicator per position/letter. A row is a coloop exactly
when an additive field-valued checksum can be zero for every other row but not
that row. This avoids guessing any particular secret substitution alphabet.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import subprocess
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def binary_rank(rows: list[list[int]]) -> int:
    basis = {}
    for row in rows:
        value = sum(1 << (26 * j + x) for j, x in enumerate(row))
        while value:
            pivot = value.bit_length() - 1
            if pivot in basis:
                value ^= basis[pivot]
            else:
                basis[pivot] = value
                break
    return len(basis)


def native_scan(worker: Path, rows: list[list[int]], q: int) -> dict:
    width = len(rows[0]) if rows else 0
    if q not in (2, 13) or not 2 <= len(rows) <= 16384 or not 1 <= width <= 16:
        raise ValueError("unsupported field, row count or width")
    if any(len(row) != width or any(not isinstance(v, int) or not 0 <= v < 26 for v in row) for row in rows):
        raise ValueError("alphabet indices 0..25 required in each cell")
    text = f"{len(rows)} {q} {width}\n" + "\n".join(" ".join(map(str, row)) for row in rows) + "\n"
    process = subprocess.run([str(worker.resolve())], input=text, capture_output=True, text=True,
                             check=True, timeout=120)
    result = json.loads(process.stdout)
    if (result.get("version"), result.get("mode"), result.get("rows"), result.get("q"), result.get("width"),
        result.get("columns"), result.get("full_marginal_rank_limit")) != (1, "onehot-additive", len(rows), q,
                                                                         width, 26 * width, 25 * width + 1):
        raise ValueError("native metadata mismatch")
    if not 0 < result["rank"] <= min(len(rows), 25 * width + 1):
        raise ValueError("native rank out of range")
    if q == 2 and result["rank"] != binary_rank(rows):
        raise ValueError("native binary rank failed independent bitset replay")
    indices = result["coloops"]
    if indices != sorted(set(indices)) or any(not 0 <= i < len(rows) for i in indices):
        raise ValueError("invalid coloop indices")
    if [record["row"] for record in result["witnesses"]] != indices[:8]:
        raise ValueError("missing native witnesses")
    for record in result["witnesses"]:
        functions = record["letter_functions"]
        if len(functions) != 26 * width or any(not isinstance(v, int) or not 0 <= v < q for v in functions):
            raise ValueError("noncanonical checksum witness")
        values = [sum(functions[26 * j + x] for j, x in enumerate(row)) % q for row in rows]
        if values != [int(i == record["row"]) for i in range(len(rows))]:
            raise ValueError("single-exception checksum did not replay")
    return result


def control_rows(q: int, seed: int = 314159) -> tuple[list[list[int]], int]:
    if q not in (2, 13):
        raise ValueError("field must be 2 or 13")
    rng = random.Random(seed)
    coefficients = [1] * 5 if q == 2 else [1, 2, 3, 5, 8]
    permutations = []
    for _ in range(5):
        permutation = list(range(26))
        rng.shuffle(permutation)
        permutations.append(permutation)
    rows, exception = [], 137
    for i in range(384):
        latent = [rng.randrange(q) for _ in range(4)]
        latent.append(((4 - sum(x * a for x, a in zip(latent, coefficients))) * pow(coefficients[4], -1, q)) % q)
        if i == exception:
            latent[4] = (latent[4] + 1) % q
        rows.append([permutations[j][x + q * rng.randrange(26 // q)] for j, x in enumerate(latent)])
    return rows, exception


def controls(worker: Path) -> list[dict]:
    output = []
    for q in (2, 13):
        rows, exception = control_rows(q)
        report = native_scan(worker, rows, q)
        if report["coloops"] != [exception]:
            raise ValueError("unknown-position-alphabet control failed")
        output.append({"synthetic": True, "q": q, "rows": len(rows), "rank": report["rank"],
                       "outlier_index": exception, "arbitrary_position_alphabets": True,
                       "checksum_witness_replayed": True})
    return output


def scan(source: str, worker: Path, width: int) -> dict:
    if not re.fullmatch(r"[A-Z]+", source) or not 1 <= width <= 16 or len(source) < 3 * width:
        raise ValueError("literal uppercase source and a supported nontrivial grouping required")
    cases = []
    for phase in range(width):
        count = (len(source) - phase) // width
        words = [source[phase + i * width:phase + (i + 1) * width] for i in range(count)]
        rows = [[ord(c) - 65 for c in word] for word in words]
        observed = [Counter(row[j] for row in rows) for j in range(width)]
        for q in (2, 13):
            report = native_scan(worker, rows, q)
            report.update(phase=phase, excluded_head=source[:phase],
                          excluded_tail=source[phase + count * width:],
                          minimum_observed_position_symbol_count=min(min(c.values()) for c in observed),
                          missing_position_symbols=sum(26 - len(c) for c in observed),
                          underdetermined=count <= 25 * width + 1,
                          exception_groups=[{"group_index": i, "letter_offset": phase + i * width,
                                             "source_word": words[i]} for i in report["coloops"]])
            cases.append(report)
    return {"status": "Exact additive-checksum test, not an accepted solution.", "source_letters": len(source),
            "letter_sha256": hashlib.sha256(source.encode()).hexdigest(), "width": width,
            "cases": cases, "case_count": len(cases),
            "cases_with_coloops": sum(bool(c["coloops"]) for c in cases),
            "cases_with_rank_deficiency": sum(c["rank"] < min(c["rows"], c["full_marginal_rank_limit"]) for c in cases),
            "caution": "Only exact additive checks with a single exception are covered. Noisy/nonlinear constructions and other groupings remain outside this test."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path)
    parser.add_argument("--worker", type=Path, required=True)
    parser.add_argument("--width", type=int, choices=(5, 7, 14), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.resolve() in (args.path.resolve(), args.worker.resolve()):
        parser.error("output must not overwrite source or worker")
    raw = args.path.read_bytes()
    body = raw.decode("ascii").splitlines()[8:]
    if not body or any(not re.fullmatch(r" *[A-Z]+(?: +[A-Z]+)* *", row) for row in body):
        parser.error("invalid original body")
    source = "".join(c for row in body for c in row if "A" <= c <= "Z")
    started = time.monotonic()
    report = scan(source, args.worker, args.width)
    report["controls"] = controls(args.worker)
    report["source_sha256"] = hashlib.sha256(raw).hexdigest()
    report["worker_source_sha256"] = hashlib.sha256((ROOT / "scripts/nachtlorn_additive_word_probe.cpp").read_bytes()).hexdigest()
    report["worker_binary_sha256"] = hashlib.sha256(args.worker.read_bytes()).hexdigest()
    report["elapsed_seconds"] = time.monotonic() - started
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("width", "case_count", "cases_with_coloops", "cases_with_rank_deficiency", "elapsed_seconds")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
