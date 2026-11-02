#!/usr/bin/env python3
"""Bounded little-endian header feasibility, not a key or plaintext search.

Optional research dependency: z3-solver. SAT witnesses are checked independently
and are not accepted as packets unless bounded decompression validates all bytes.
UNKNOWN, including timeouts, is never converted into UNSAT.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.binary_envelope_probe import decompress_member  # noqa: E402
from scripts.nachtlorn_prefix_invariants import (  # noqa: E402
    ALPHABET,
    header_catalog,
    numeral,
    numeric_bounds,
    validate,
)

try:
    import z3
except ImportError:
    z3 = None


SEED = 4300
TIMEOUT_MS = 15000


def residue_coefficients(text: str, bits: int, *, alphabet: str = ALPHABET,
                         bias: int = 0) -> tuple[dict[str, int], int]:
    validate(text, alphabet, bias)
    if bits < 1:
        raise ValueError("positive modulus width required")
    modulus = 1 << bits
    coefficients = dict.fromkeys(alphabet, 0)
    power, geometric = 1, 0
    for glyph in reversed(text):
        coefficients[glyph] = (coefficients[glyph] + power) % modulus
        geometric = (geometric + power) % modulus
        power = power * len(alphabet) % modulus
        if power == 0:
            break
    return coefficients, bias * geometric % modulus


def symbolic_value(digits: dict, coefficients: dict[str, int], shift: int, bits: int, digit_bits: int):
    value = z3.BitVecVal(shift, bits)
    for glyph, coefficient in coefficients.items():
        if coefficient:
            value += coefficient * z3.ZeroExt(bits - digit_bits, digits[glyph])
    return value


def build_query(text: str, headers: tuple[bytes, ...], *, alphabet: str = ALPHABET,
                bias: int = 0, timeout_ms: int = TIMEOUT_MS, fixed: dict[str, int] | None = None):
    if z3 is None:
        raise RuntimeError("z3-solver research dependency is required; missing solver is not an UNSAT result")
    validate(text, alphabet, bias)
    fixed = dict(fixed or {})
    if (not headers or not headers[0] or len({len(h) for h in headers}) != 1 or timeout_ms < 1
            or not set(fixed) <= set(alphabet) or len(set(fixed.values())) != len(fixed)
            or any(not isinstance(v, int) or not 0 <= v < len(alphabet) for v in fixed.values())):
        raise ValueError("same-width nonempty headers, positive timeout and valid fixed mapping required")
    bits = 8 * len(headers[0])
    digit_bits = (len(alphabet) - 1).bit_length()
    digits = {glyph: z3.BitVec(f"digit_{index}", digit_bits) for index, glyph in enumerate(alphabet)}
    solver = z3.SolverFor("QF_BV")
    solver.set(timeout=timeout_ms, random_seed=SEED)
    solver.add(z3.Distinct(*digits.values()))
    for glyph, digit in digits.items():
        solver.add(z3.ULE(digit, len(alphabet) - 1))
        if glyph in fixed:
            solver.add(digit == fixed[glyph])
    coefficients, shift = residue_coefficients(text, bits, alphabet=alphabet, bias=bias)
    value = symbolic_value(digits, coefficients, shift, bits, digit_bits)
    solver.add(z3.Or(*(value == int.from_bytes(header, "little") for header in headers)))
    # Residues alone would permit truncating a zero at the high end of a short
    # synthetic header. The real source's numeric lower bound already suffices.
    lower, upper = numeric_bounds(text, alphabet, bias)
    threshold = 1 << (bits - 8)
    if upper < threshold:
        solver.add(z3.BoolVal(False))
    elif lower < threshold:
        full_bits = max(bits, upper.bit_length() + 1)
        full_coefficients, full_shift = residue_coefficients(text, full_bits, alphabet=alphabet, bias=bias)
        full_value = symbolic_value(digits, full_coefficients, full_shift, full_bits, digit_bits)
        solver.add(z3.UGE(full_value, threshold))
    return solver, digits


def exact_roundtrip(text: str, mapping: dict[str, int], value: int, base: int, bias: int) -> bool:
    reverse = {digit: glyph for glyph, digit in mapping.items()}
    output = []
    for _ in text:
        value, digit = divmod(value - bias, base)
        output.append(reverse[digit])
    return value == 0 and "".join(reversed(output)) == text


def solve_family(text: str, headers: tuple[bytes, ...], *, alphabet: str = ALPHABET,
                 bias: int = 0, timeout_ms: int = TIMEOUT_MS, fixed: dict[str, int] | None = None) -> dict:
    solver, digits = build_query(text, headers, alphabet=alphabet, bias=bias,
                                timeout_ms=timeout_ms, fixed=fixed)
    formula_hash = hashlib.sha256(solver.to_smt2().encode("utf-8")).hexdigest()
    started = time.monotonic()
    answer = solver.check()
    elapsed = round(time.monotonic() - started, 6)
    common = {"timeout_ms": timeout_ms, "elapsed_seconds": elapsed,
              "smt2_sha256": formula_hash, "header_alternatives": len(headers)}
    if answer == z3.unsat:
        return {**common, "status": "unsat", "meaning": "No digit alphabet in this model matches any admitted header."}
    if answer != z3.sat:
        return {**common, "status": "unknown", "reason": solver.reason_unknown(),
                "meaning": "Feasibility unresolved; this is not a negative result."}
    model = solver.model()
    mapping = {glyph: model.eval(digit, model_completion=True).as_long() for glyph, digit in digits.items()}
    if set(mapping.values()) != set(range(len(alphabet))):
        raise AssertionError("solver returned a non-bijective mapping")
    value = numeral(text, mapping, len(alphabet), bias)
    data = value.to_bytes(max(1, (value.bit_length() + 7) // 8), "little")
    matching = next((header for header in headers if data.startswith(header)), None)
    roundtrip = exact_roundtrip(text, mapping, value, len(alphabet), bias)
    if matching is None or not roundtrip:
        raise AssertionError("SAT witness failed independent integer/header/roundtrip validation")
    return {**common, "status": "sat", "meaning": "One arbitrary header-compatible alphabet; not a recovered key.",
            "witness": {"digit_alphabet": "".join(sorted(mapping, key=mapping.get)),
                        "bytes": len(data), "prefix_hex": data[:16].hex(), "matched_header_hex": matching.hex(),
                        "binary_sha256": hashlib.sha256(data).hexdigest(),
                        "exact_retained_letter_roundtrip": roundtrip,
                        "canonical_numeral": bias == 1 or mapping[text[0]] != 0}}


def check_witness(text: str, result: dict, kind: str, bias: int) -> dict:
    """Validate only the reported SAT witness, never all compatible alphabets."""
    alphabet = result["witness"]["digit_alphabet"]
    mapping = {glyph: i for i, glyph in enumerate(alphabet)}
    value = numeral(text, mapping, 26, bias)
    data = value.to_bytes(max(1, (value.bit_length() + 7) // 8), "little")
    accepted = []
    for zeros in range(8):
        packet = data + b"\0" * zeros
        decoded = decompress_member(packet, kind)
        if decoded is None or decoded[1] != len(packet):
            continue
        payload, consumed = decoded
        accepted.append({"restored_trailing_zero_bytes": zeros, "consumed_bytes": consumed,
                         "output_bytes": len(payload), "output_sha256": hashlib.sha256(payload).hexdigest()})
    return {"complete_stream_verified": bool(accepted), "accepted_records": accepted,
            "zero_restorations_tested": 8,
            "scope": "Only this arbitrary witness, output cap1MiB, XZ memory cap64MiB, no preset dictionary. Population/outlier unassigned."}


def scan(text: str, timeout_ms: int = TIMEOUT_MS) -> dict:
    if z3 is None:
        raise RuntimeError("z3-solver research dependency required")
    validate(text, ALPHABET, 0)
    catalog = header_catalog()
    cases = []
    for drop in (False, True):
        if drop and (not text.endswith("I") or len(text) < 2):
            continue
        retained = text[:-1] if drop else text
        for bias in (0, 1):
            families = []
            for kind, headers in catalog.items():
                result = solve_family(retained, headers, bias=bias, timeout_ms=timeout_ms)
                if result["status"] == "sat":
                    result["witness_packet_check"] = check_witness(retained, result, kind, bias)
                families.append({"format": kind, **result})
                print(json.dumps({"drop_final_i": drop, "bias": bias, "format": kind,
                                  "status": result["status"], "elapsed_seconds": result["elapsed_seconds"]}), flush=True)
            cases.append({"drop_final_i": drop, "bias": bias, "retained_letters": len(retained),
                          "families": families})
    return {"status": "Bounded little-endian header feasibility; no answer selected by words.",
            "source_letters": len(text), "letter_sha256": hashlib.sha256(text.encode("ascii")).hexdigest(),
            "solver": {"version": z3.get_version_string(), "package_version": version("z3-solver"),
                       "random_seed": SEED, "timeout_ms_per_query": timeout_ms},
            "headers": {kind: [h.hex() for h in headers] for kind, headers in catalog.items()}, "cases": cases,
            "limits": ["SAT proves header compatibility only; one arbitrary witness is checked per SAT query.",
                       "UNSAT excludes only the specified raw little-endian representation/header family.",
                       "UNKNOWN or timeout is unresolved feasibility, never a negative.",
                       "No extra cipher, reversed digit order, block packing, offsets, passwords or book transformations."]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-ms", type=int, default=TIMEOUT_MS)
    args = parser.parse_args(argv)
    if args.path.resolve() == args.output.resolve():
        parser.error("output must not overwrite the source")
    if args.timeout_ms < 1:
        parser.error("timeout must be positive")
    raw = args.path.read_bytes()
    rows = raw.decode("ascii").splitlines()[8:]
    if not rows or any(not re.fullmatch(r" *[A-Z]+(?: +[A-Z]+)* *", row) for row in rows):
        parser.error("expected the original ASCII body")
    text = "".join(c for row in rows for c in row if "A" <= c <= "Z")
    report = scan(text, args.timeout_ms)
    report["source_sha256"] = hashlib.sha256(raw).hexdigest()
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
