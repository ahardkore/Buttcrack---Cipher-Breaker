#!/usr/bin/env python3
"""Look for higher-order modular dependence across literal five-letter groups.

All linear directions over F_2 and F_13 are tested; whole-base26 numeric residues
are a much smaller family. No English scoring or preferred outlier is used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.binary_envelope_probe import A26, keyed_alphabet  # noqa: E402

ALPHABETS = {"standard": A26, "BLOOM": keyed_alphabet("BLOOM"),
             "NACHTLORN": keyed_alphabet("NACHTLORN")}
MODULI = (2, 13)


def projective_directions(q: int):
    if q not in (2, 5, 13):
        raise ValueError("supported prime fields are 2, 5 and 13")
    for pivot in range(5):
        for code in range(q ** (4 - pivot)):
            a = [0] * 5
            a[pivot] = 1
            for j in range(4, pivot, -1):
                code, a[j] = divmod(code, q)
            yield a


def histogram(rows: list[list[int]], coefficients: list[int], q: int) -> list[int]:
    result = [0] * q
    for row in rows:
        result[sum(x * a for x, a in zip(row, coefficients)) % q] += 1
    return result


def native_scan(worker: Path, rows: list[list[int]], q: int) -> dict:
    if q not in (2, 5, 13) or not 2 <= len(rows) <= 16384:
        raise ValueError("unsupported modulus or row count")
    if any(len(row) != 5 or any(not isinstance(x, int) or not 0 <= x < q for x in row) for row in rows):
        raise ValueError("five canonical field elements required per row")
    text = f"{len(rows)} {q}\n" + "\n".join(" ".join(map(str, row)) for row in rows) + "\n"
    result = subprocess.run([str(worker.resolve())], input=text, capture_output=True, text=True,
                            check=True, timeout=120)
    report = json.loads(result.stdout)
    if (report.get("version"), report.get("columns"), report.get("q"), report.get("rows"),
        report.get("directions")) != (1, 5, q, len(rows), (q ** 5 - 1) // (q - 1)):
        raise ValueError("native worker metadata mismatch")
    top = report.get("top", [])
    if len(top) != 8:
        raise ValueError("native worker must return eight directions")
    previous = None
    for record in top:
        a = record["coefficients"]
        if (len(a) != 5 or not any(a) or any(not isinstance(v, int) or not 0 <= v < q for v in a)
                or next(v for v in a if v) != 1):
            raise ValueError("noncanonical native direction")
        counts = histogram(rows, a, q)
        squares = sum(x * x for x in counts)
        statistic = q * squares / len(rows) - len(rows)
        dominant = counts.index(max(counts))
        exceptions = [i for i, row in enumerate(rows)
                      if sum(x * v for x, v in zip(row, a)) % q != dominant]
        wanted = exceptions if max(counts) == len(rows) - 1 and counts.count(max(counts)) == 1 else []
        if (counts != record["histogram"] or squares != record["sum_squares"]
                or not math.isclose(statistic, record["statistic"], abs_tol=1e-10)
                or dominant != record["dominant_residue"] or max(counts) != record["dominant_count"]
                or wanted != record["unique_exception_indices"]):
            raise ValueError("native record did not replay")
        order = (-squares, a)
        if previous is not None and order <= previous:
            raise ValueError("native ranking is not strict and deterministic")
        previous = order
    return report


def control_rows(seed: int = 271828) -> tuple[list[list[int]], list[int], int]:
    """An exact affine check with one error; synthetic, not puzzle evidence."""
    rng = random.Random(seed)
    q, a, intercept, exception = 13, [1, 2, 3, 5, 8], 4, 137
    rows = []
    for _ in range(257):
        row = [rng.randrange(q) for _ in range(4)]
        row.append(((intercept - sum(x * v for x, v in zip(row, a))) * pow(a[4], -1, q)) % q)
        rows.append(row)
    rows[exception][4] = (rows[exception][4] + 1) % q
    return rows, a, exception


def controls(worker: Path) -> dict:
    rows, a, exception = control_rows()
    original = native_scan(worker, rows, 13)
    if original["top"][0]["coefficients"] != a or original["top"][0]["unique_exception_indices"] != [exception]:
        raise ValueError("synthetic single-error control failed")
    # Invertible upper triangular mixing plus translation changes all five
    # coordinates while preserving the complete family of projection scores.
    mixed = [[(sum((j - i + 1) * row[j] for j in range(i, 5)) + i + 2) % 13
              for i in range(5)] for row in rows]
    transformed = native_scan(worker, mixed, 13)
    if (transformed["top"][0]["sum_squares"] != original["top"][0]["sum_squares"]
            or transformed["top"][0]["unique_exception_indices"] != [exception]):
        raise ValueError("affine-mixing control failed")
    # Relabeling samples may not change a direction's histogram or best score.
    reordered = native_scan(worker, list(reversed(rows)), 13)
    if (reordered["top"][0]["sum_squares"] != original["top"][0]["sum_squares"]
            or reordered["top"][0]["unique_exception_indices"] != [len(rows) - 1 - exception]):
        raise ValueError("sample reversal control failed")
    return {"synthetic": True, "rows": len(rows), "coefficients": a,
            "outlier_index": exception, "directions": original["directions"],
            "single_error": True, "affine_mixing": True, "sample_reversal": True}


def scan(source: str, alphabet: str, worker: Path, nulls: int = 31, seed: int = 20261101) -> dict:
    if not re.fullmatch(r"[A-Z]+", source) or len(source) // 5 < 2:
        raise ValueError("literal uppercase source with at least two complete groups required")
    if len(alphabet) != 26 or set(alphabet) != set(A26) or not 0 <= nulls <= 1000:
        raise ValueError("alphabet must permute A..Z; null count must be 0..1000")
    words = [source[i:i + 5] for i in range(0, (len(source) // 5) * 5, 5)]
    coordinates = [[alphabet.index(c) for c in word] for word in words]
    actual = {str(q): native_scan(worker, [[v % q for v in row] for row in coordinates], q)
              for q in MODULI}
    for report in actual.values():
        for record in report["top"]:
            record["exception_groups"] = [{"group_index": i, "source_word": words[i]}
                                           for i in record["unique_exception_indices"]]
    rng = random.Random(seed)
    null_results = []
    for replicate in range(nulls):
        permutations = []
        for _ in range(5):
            indices = list(range(len(words)))
            rng.shuffle(indices)
            permutations.append(indices)
        sample = [[coordinates[permutations[j][i]][j] for j in range(5)] for i in range(len(words))]
        maxima = {str(q): native_scan(worker, [[v % q for v in row] for row in sample], q)["top"][0]["statistic"]
                  for q in MODULI}
        null_results.append({"replicate": replicate, "maxima": maxima, "family_maximum": max(maxima.values())})
    maximum = max(r["top"][0]["statistic"] for r in actual.values())
    exceed = sum(r["family_maximum"] >= maximum for r in null_results)
    return {"status": "Structural test only, not an accepted solution.", "alphabet": alphabet,
            "source_letters": len(source), "complete_groups": len(words), "unconsumed_tail": source[len(words) * 5:],
            "letter_sha256": hashlib.sha256(source.encode()).hexdigest(), "moduli": list(MODULI),
            "actual": actual, "actual_family_maximum": maximum, "null_seed": seed,
            "null_method": "Independent within-column permutations, shared across moduli and alphabet workers.",
            "null_results": null_results, "null_maxima_at_least_actual": exceed,
            "smoothed_upper_fraction": (1 + exceed) / (1 + nulls),
            "caution": "Raw Pearson statistics are scores, not chi-square p-values. Conditional family only; not a global search correction."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path)
    parser.add_argument("--worker", type=Path, required=True, help="compiled trusted modular_word_probe worker")
    parser.add_argument("--alphabet", choices=ALPHABETS, required=True)
    parser.add_argument("--nulls", type=int, default=31)
    parser.add_argument("--seed", type=int, default=20261101)
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
    report = scan(source, ALPHABETS[args.alphabet], args.worker, args.nulls, args.seed)
    report["controls"] = controls(args.worker)
    report["alphabet_name"] = args.alphabet
    report["source_sha256"] = hashlib.sha256(raw).hexdigest()
    report["worker_source_sha256"] = hashlib.sha256((ROOT / "scripts/nachtlorn_modular_word_probe.cpp").read_bytes()).hexdigest()
    report["worker_binary_sha256"] = hashlib.sha256(args.worker.read_bytes()).hexdigest()
    report["elapsed_seconds"] = time.monotonic() - started
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("alphabet_name", "actual_family_maximum", "null_maxima_at_least_actual", "elapsed_seconds")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
