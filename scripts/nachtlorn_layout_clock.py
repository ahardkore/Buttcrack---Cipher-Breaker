#!/usr/bin/env python3
"""R19: native shared-RNG recipes must predict the original indentation exactly.

This tests the construction clock, not cipher letters, plaintext, or an outlier.
No seeds, prefix offsets, alphabets or word fragments are searched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from pathlib import Path

METHODS = ("randrange26", "choices26", "bits5_mod26", "bits8_mod26", "row_randbytes_mod26")
SCHEDULES = ("indent_then_row", "row_then_indent", "all_rows_then_indents")
SEED = 4300


class TracedRandom(random.Random):
    """Delegate unchanged to native Random while recording MT word consumption."""
    def __init__(self, seed):
        super().__init__(seed)
        self.words = 0

    def getrandbits(self, k):
        value = super().getrandbits(k)
        self.words += (k + 31) // 32
        return value

    def random(self):
        value = super().random()
        self.words += 2
        return value


def letter_batch(rng, method: str, size: int) -> list[int]:
    if method not in METHODS or type(size) is not int or size < 0:
        raise ValueError("registered method and nonnegative integer batch size required")
    if method == "randrange26":
        return [rng.randrange(26) for _ in range(size)]
    if method == "choices26":
        return rng.choices(range(26), k=size)
    if method == "bits5_mod26":
        return [rng.getrandbits(5) % 26 for _ in range(size)]
    if method == "bits8_mod26":
        return [rng.getrandbits(8) % 26 for _ in range(size)]
    return [value % 26 for value in rng.randbytes(size)]


def simulate(lengths: list[int], method: str | None, schedule: str, *, seed: int = SEED) -> dict:
    if (not lengths or any(type(n) is not int or n < 1 for n in lengths)
            or schedule not in SCHEDULES or (method is not None and method not in METHODS)):
        raise ValueError("positive row sizes, registered schedule and method required")
    rng = TracedRandom(seed)
    indents, words_before = [], []

    def letters(size):
        if method is not None:
            letter_batch(rng, method, size)  # Outputs are intentionally not read as plaintext.

    def indent():
        words_before.append(rng.words)
        indents.append(rng.randrange(8))

    if schedule == "all_rows_then_indents":
        for size in lengths:
            letters(size)
        for _ in lengths:
            indent()
    else:
        for size in lengths:
            if schedule == "indent_then_row":
                indent()
                letters(size)
            else:
                letters(size)
                indent()
    state_hash = hashlib.sha256(json.dumps(rng.getstate(), separators=(",", ":")).encode()).hexdigest()
    return {"predicted_indents": indents, "words_before_indents": words_before,
            "total_mt_words": rng.words, "final_state_sha256": state_hash}


def compare(observed: list[int], predicted: dict) -> dict:
    values = predicted["predicted_indents"]
    if len(observed) != len(values) or any(type(n) is not int or not 0 <= n < 8 for n in observed):
        raise ValueError("one observed indent0..7 per predicted row required")
    mismatches = [{"body_row": i + 1, "observed": actual, "predicted": expected,
                   "mt_words_before_indent": predicted["words_before_indents"][i]}
                  for i, (actual, expected) in enumerate(zip(observed, values)) if actual != expected]
    return {"matches": len(values) - len(mismatches), "mismatches": len(mismatches),
            "exact_layout_match": not mismatches,
            "matching_prefix_rows": mismatches[0]["body_row"] - 1 if mismatches else len(values),
            "first_mismatches": mismatches[:10], "total_mt_words": predicted["total_mt_words"],
            "final_state_sha256": predicted["final_state_sha256"]}


def scan(lengths: list[int], observed: list[int], *, seed: int = SEED) -> dict:
    baseline = simulate(lengths, None, "indent_then_row", seed=seed)
    baseline_result = compare(observed, baseline)
    groups, cases = {}, []
    for schedule in SCHEDULES:
        for method in METHODS:
            prediction = simulate(lengths, method, schedule, seed=seed)
            key = tuple(prediction["predicted_indents"])
            if key not in groups:
                groups[key] = {"id": len(groups) + 1, "predicted_indents": list(key), "members": []}
            groups[key]["members"].append({"method": method, "schedule": schedule})
            cases.append({"method": method, "schedule": schedule, "prediction_group": groups[key]["id"],
                          **compare(observed, prediction)})
    return {"status": "Exact layout-clock compatibility, not body decryption.",
            "seed": seed, "python_version": sys.version.split()[0], "rows": len(lengths),
            "row_lengths": lengths, "observed_indents": observed,
            "baseline": {"model": "consecutive indent draws only (known R0 baseline)", **baseline_result},
            "cases": cases, "distinct_prediction_groups": len(groups), "prediction_groups": list(groups.values()),
            "limits": ["Failures reject only registered same-instance native recipes, not all shared-RNG constructions.",
                       "RNG offsets, separate instances, reset/reseed, state restoration and extra calls are outside scope.",
                       "Identical indentation predictions are clock aliases, not independent evidence.",
                       "A compatible layout alone would not identify generated letters, a population or an outlier."]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.path.resolve() == args.output.resolve():
        parser.error("output must not overwrite the source")
    raw = args.path.read_bytes()
    rows = raw.decode("ascii").splitlines()[8:]
    if not rows or any(not re.fullmatch(r" *[A-Z]+(?: +[A-Z]+)* *", row) for row in rows):
        parser.error("expected original ASCII body after eight-line preamble")
    observed = [len(row) - len(row.lstrip(" ")) for row in rows]
    lengths = [sum("A" <= c <= "Z" for c in row) for row in rows]
    result = scan(lengths, observed)
    result["source_sha256"] = hashlib.sha256(raw).hexdigest()
    result["source_bytes"] = len(raw)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cases": len(result["cases"]), "exact_matches": sum(c["exact_layout_match"] for c in result["cases"]),
                      "distinct_prediction_groups": result["distinct_prediction_groups"],
                      "baseline_exact": result["baseline"]["exact_layout_match"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
