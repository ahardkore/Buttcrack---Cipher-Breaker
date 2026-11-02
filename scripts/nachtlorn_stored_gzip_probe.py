#!/usr/bin/env python3
"""Whole-packet stored-gzip test; bounded incomplete searches are not exclusions.

No semantic key, plaintext score, or population is assumed. SMT enumerates only
assignments satisfying both the stored-block structure and the far-end ISIZE;
ordinary Python checks each entire packet and its CRC before accepting it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import time
import zlib
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import nachtlorn_little_endian_probe as le  # noqa: E402
from scripts.binary_envelope_probe import decompress_member  # noqa: E402
from scripts.nachtlorn_prefix_invariants import (  # noqa: E402
    ALPHABET,
    numeral,
    numeric_bounds,
    prefix_interval,
    validate,
)

z3 = le.z3
BUDGET_MS = 30000
CANDIDATE_CAP = 512


def interval_covers(text: str, lower: int, upper: int, *, alphabet: str = ALPHABET,
                    bias: int = 0) -> list[dict[str, int]]:
    """Disjoint exact prefix cylinders covering all interval-compatible maps."""
    validate(text, alphabet, bias)
    if lower > upper:
        raise ValueError("ordered interval required")
    base = len(alphabet)
    span = base ** len(text)
    shift = bias * (span - 1) // (base - 1)
    low, high = max(0, lower - shift), min(span - 1, upper - shift)
    stack = [(0, 0, span, {})] if low <= high else []
    covers = []
    while stack:
        index, start, width, mapping = stack.pop()
        end = start + width - 1
        if end < low or start > high:
            continue
        if low <= start and end <= high:
            covers.append(mapping)
            continue
        unit = width // base
        glyph = text[index]
        first, last = (max(low, start) - start) // unit, (min(high, end) - start) // unit
        used = set(mapping.values())
        choices = [mapping[glyph]] if glyph in mapping else range(first, last + 1)
        for digit in choices:
            if first <= digit <= last and (glyph in mapping or digit not in used):
                following = mapping if glyph in mapping else {**mapping, glyph: digit}
                stack.append((index + 1, start + digit * unit, unit, following))
    return covers


def length_cases(text: str, bias: int = 0) -> list[dict]:
    lower, upper = numeric_bounds(text, bias=bias)
    first = max(1, (lower.bit_length() + 7) // 8)
    last = max(1, (upper.bit_length() + 7) // 8)
    cases = []
    for size in range(first, last + 1):
        for zeros in range(8):
            payload_bytes = size + zeros - 23
            if not 1 <= payload_bytes <= 65535:
                continue
            trailer = payload_bytes.to_bytes(4, "little")
            stripped = trailer.rstrip(b"\0")
            if 4 - len(stripped) != zeros:
                continue
            high_prefix = stripped[::-1]
            cases.append({"minimal_bytes": size, "restored_trailing_zero_bytes": zeros,
                          "payload_bytes": payload_bytes, "high_prefix_hex": high_prefix.hex()})
    return cases


def build_stored_query(text: str, bias: int, case: dict, covers: list[dict],
                       fixed: dict[str, int] | None = None):
    if z3 is None:
        raise RuntimeError("optional z3-solver required; missing solver is not an exclusion")
    fixed = dict(fixed or {})
    if (not set(fixed) <= set(ALPHABET) or len(set(fixed.values())) != len(fixed)
            or any(not isinstance(v, int) or not 0 <= v < 26 for v in fixed.values())):
        raise ValueError("injective in-range fixed assignments required")
    digits = {glyph: z3.BitVec(f"digit_{glyph}", 5) for glyph in ALPHABET}
    solver = z3.SolverFor("QF_BV")
    solver.set(random_seed=le.SEED)
    solver.add(z3.Distinct(*digits.values()))
    for glyph, digit in digits.items():
        solver.add(z3.ULE(digit, 25))
        if glyph in fixed:
            solver.add(digit == fixed[glyph])
    solver.add(z3.Or(*(z3.And(*(digits[glyph] == digit for glyph, digit in cover.items())) for cover in covers)))
    coefficients, shift = le.residue_coefficients(text, 120, bias=bias)
    low = le.symbolic_value(digits, coefficients, shift, 120, 5)
    size = case["payload_bytes"]
    solver.add(z3.Extract(31, 0, low) == int.from_bytes(b"\x1f\x8b\x08\0", "little"))
    solver.add(z3.Extract(82, 80, low) == 1)  # byte10: BFINAL=1, BTYPE=00
    solver.add(z3.Extract(103, 88, low) == size)
    solver.add(z3.Extract(119, 104, low) == (size ^ 65535))
    return solver, digits


def verify_packet(packet: bytes) -> dict:
    """Independently parse this exact class and validate its whole checksum."""
    if len(packet) < 24 or packet[:4] != b"\x1f\x8b\x08\0" or packet[10] & 7 != 1:
        return {"grammar_valid": False, "complete_stream_verified": False}
    size = int.from_bytes(packet[11:13], "little")
    complement = int.from_bytes(packet[13:15], "little")
    if not 1 <= size <= 65535 or complement != size ^ 65535 or len(packet) != size + 23:
        return {"grammar_valid": False, "complete_stream_verified": False}
    payload = packet[15:-8]
    isize = int.from_bytes(packet[-4:], "little")
    if isize != size:
        return {"grammar_valid": False, "complete_stream_verified": False}
    stored_crc = int.from_bytes(packet[-8:-4], "little")
    actual_crc = zlib.crc32(payload) & 0xffffffff
    decoded = decompress_member(packet, "gzip")
    verified = (stored_crc == actual_crc and decoded is not None
                and decoded[0] == payload and decoded[1] == len(packet))
    return {"grammar_valid": True, "crc32_valid": stored_crc == actual_crc, "isize_valid": True,
            "stored_crc32": f"{stored_crc:08x}", "computed_crc32": f"{actual_crc:08x}",
            "payload_bytes": size, "payload_sha256": hashlib.sha256(payload).hexdigest(),
            "complete_stream_verified": verified}


def search_case(text: str, bias: int, case: dict, *, budget_ms: int = BUDGET_MS,
                candidate_cap: int = CANDIDATE_CAP, fixed: dict[str, int] | None = None,
                solver_adapter=None) -> dict:
    validate(text, ALPHABET, bias)
    if budget_ms < 1 or candidate_cap < 1:
        raise ValueError("positive case budget and candidate cap required")
    started = time.monotonic()
    deadline = started + budget_ms / 1000
    lo, hi = prefix_interval(bytes.fromhex(case["high_prefix_hex"]), case["minimal_bytes"])
    covers = interval_covers(text, lo, hi, bias=bias)
    common = {**case, "interval_prefix_covers": len(covers),
              "prefix_compatible_alphabet_mappings": sum(math.factorial(26 - len(c)) for c in covers),
              "budget_ms": budget_ms, "candidate_cap": candidate_cap}
    audits = []

    def finish(status, **extra):
        return {**common, "status": status, "candidate_numerals_checked": len(audits),
                "candidate_audits": audits, "elapsed_seconds": round(time.monotonic() - started, 6), **extra}

    if not covers:
        return finish("empty_interval_cover", exact_exclusion=True,
                      meaning="No alphabet matches the minimal-width ISIZE trailer, before any CRC search.")
    solver, digits = build_stored_query(text, bias, case, covers, fixed)
    initial_smt2 = solver.to_smt2()
    formula_hash = hashlib.sha256(initial_smt2.encode()).hexdigest()
    if solver_adapter is not None:
        solver = solver_adapter(initial_smt2)
    while True:
        remaining = int((deadline - time.monotonic()) * 1000)
        if remaining < 1:
            return finish("budget_exhausted", exact_exclusion=False, initial_smt2_sha256=formula_hash)
        solver.set(timeout=remaining)
        answer = solver.check()
        if answer == z3.unsat:
            return finish("exhausted_no_packet", exact_exclusion=True, initial_smt2_sha256=formula_hash,
                          meaning="All structurally compatible distinct numerals in this case were checked; none validates.")
        if answer != z3.sat:
            return finish("unknown", exact_exclusion=False, reason=solver.reason_unknown(),
                          initial_smt2_sha256=formula_hash)
        model = solver.model()
        mapping = {glyph: model.eval(digit, model_completion=True).as_long() for glyph, digit in digits.items()}
        if set(mapping.values()) != set(range(26)):
            raise AssertionError("non-bijective solver witness")
        value = numeral(text, mapping, 26, bias)
        minimal = value.to_bytes(max(1, (value.bit_length() + 7) // 8), "little")
        roundtrip = le.exact_roundtrip(text, mapping, value, 26, bias)
        if len(minimal) != case["minimal_bytes"] or not roundtrip:
            raise AssertionError("witness violates numeric interval or retained-source roundtrip")
        packet = minimal + b"\0" * case["restored_trailing_zero_bytes"]
        checks = verify_packet(packet)
        if not checks["grammar_valid"]:
            raise AssertionError("SMT witness fails independent packet grammar")
        audits.append({"digit_alphabet": "".join(sorted(mapping, key=mapping.get)),
                       "minimal_binary_sha256": hashlib.sha256(minimal).hexdigest(),
                       "packet_sha256": hashlib.sha256(packet).hexdigest(),
                       "exact_retained_letter_roundtrip": roundtrip, "packet_checks": checks})
        if checks["complete_stream_verified"]:
            return finish("verified_packet", exact_exclusion=False, initial_smt2_sha256=formula_hash,
                          meaning="Complete checksum-valid member; population/outlier still unassigned.")
        # Ignore unused-symbol permutations: they produce exactly the same
        # numeral. All source-observed symbol assignments are still exhausted.
        solver.add(z3.Or(*(digits[glyph] != mapping[glyph] for glyph in sorted(set(text)))))
        if len(audits) >= candidate_cap:
            return finish("candidate_cap", exact_exclusion=False, initial_smt2_sha256=formula_hash)


def scan(text: str, budget_ms: int = BUDGET_MS, candidate_cap: int = CANDIDATE_CAP) -> dict:
    if z3 is None:
        raise RuntimeError("optional z3-solver required; absent dependency is not a negative result")
    validate(text, ALPHABET, 0)
    models = []
    for drop in (False, True):
        if drop and (not text.endswith("I") or len(text) < 2):
            continue
        retained = text[:-1] if drop else text
        for bias in (0, 1):
            cases = []
            for case in length_cases(retained, bias):
                result = search_case(retained, bias, case, budget_ms=budget_ms, candidate_cap=candidate_cap)
                cases.append(result)
                print(json.dumps({"drop_final_i": drop, "bias": bias, "minimal_bytes": case["minimal_bytes"],
                                  "status": result["status"], "checked": result["candidate_numerals_checked"],
                                  "elapsed_seconds": result["elapsed_seconds"]}), flush=True)
            models.append({"drop_final_i": drop, "bias": bias, "retained_letters": len(retained), "cases": cases})
    return {"status": "Whole-packet single-stored-block gzip test; no word/answer scoring.",
            "source_letters": len(text), "letter_sha256": hashlib.sha256(text.encode("ascii")).hexdigest(),
            "solver": {"version": z3.get_version_string(), "package_version": version("z3-solver"),
                       "seed": le.SEED, "case_budget_ms": budget_ms, "candidate_cap": candidate_cap},
            "models": models,
            "scope": "FLG0, ten-byte gzip header, one nonempty final stored DEFLATE block, <=65535 payload bytes, valid CRC32/ISIZE; 0..7 trailing-zero restorations.",
            "limits": ["Other gzip headers/block types or multiple blocks/members are not tested.",
                       "Only empty covers or completed UNSAT enumeration are exclusions.",
                       "Timeout, UNKNOWN or candidate cap leaves the case unresolved.",
                       "A valid packet would not itself identify a population or outlier."]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--budget-ms", type=int, default=BUDGET_MS)
    parser.add_argument("--candidate-cap", type=int, default=CANDIDATE_CAP)
    args = parser.parse_args(argv)
    if args.path.resolve() == args.output.resolve():
        parser.error("output must not overwrite the source")
    if args.budget_ms < 1 or args.candidate_cap < 1:
        parser.error("positive budget and candidate cap required")
    raw = args.path.read_bytes()
    rows = raw.decode("ascii").splitlines()[8:]
    if not rows or any(not re.fullmatch(r" *[A-Z]+(?: +[A-Z]+)* *", row) for row in rows):
        parser.error("expected original ASCII body")
    text = "".join(c for row in rows for c in row if "A" <= c <= "Z")
    report = scan(text, args.budget_ms, args.candidate_cap)
    report["source_sha256"] = hashlib.sha256(raw).hexdigest()
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
