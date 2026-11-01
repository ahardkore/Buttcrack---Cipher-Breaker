#!/usr/bin/env python3
"""Screen headerless numeric objects after whole-integer base-26 recovery.

Bit-lane bias is a structural screen, not a p-value or a recovered answer. Numeric
interpretations are attempted only for flagged buffers; no English gate is used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.binary_envelope_probe import ALPHABETS, decode_base26  # noqa: E402
from scripts.binary_text_probe import apply_mask, mask_specs  # noqa: E402
from scripts.nachtlorn_binary_research import KEYS, variants  # noqa: E402

PERIODS = (2, 4, 8, 20, 36, 40, 72)
# IEEE floats in the declared magnitude range have opposite top two exponent
# bits, even when their individual marginals are balanced. Uppercase ASCII XOR
# preserves this parity bias (possibly complementing it).
PARITY_MASKS = tuple(1 << bit for bit in range(8)) + (0x60,)
TABLES = tuple(bytes(bin(i & mask).count("1") & 1 for i in range(256)) for mask in PARITY_MASKS)


def bit_profile(data: bytes) -> dict:
    best = {"score": 0.0}
    for period in PERIODS:
        for phase in range(period):
            lane = data[phase::period]
            n = len(lane)
            if n < 64:
                continue
            root_n = math.sqrt(n)
            for mask, table in zip(PARITY_MASKS, TABLES):
                ones = sum(lane.translate(table))
                score = abs(2 * ones - n) / root_n
                if score > best["score"]:
                    best = {"score": score, "period": period, "phase": phase,
                            "bit": mask.bit_length() - 1 if mask & (mask - 1) == 0 else None,
                            "parity_mask": mask, "ones": ones, "observations": n}
    return best


def numeric_candidates(data: bytes) -> list[dict]:
    results = []
    for spec in mask_specs(KEYS):
        decoded = apply_mask(data, spec)
        for reverse in (False, True):
            value = decoded[::-1] if reverse else decoded
            for offset in range(32):
                for code, width in (("f", 4), ("d", 8)):
                    n = (len(value) - offset) // width
                    if n < 64:
                        continue
                    block = value[offset:offset + n * width]
                    for endian in ("<", ">"):
                        floats = [x[0] for x in struct.iter_unpack(endian + code, block)]
                        sane = sum(math.isfinite(x) and (x == 0 or 1e-12 <= abs(x) <= 1e12) for x in floats)
                        if sane < n - 1:
                            continue
                        finite = sorted(x for x in floats if math.isfinite(x))
                        if not finite:
                            continue
                        q1, q3 = finite[len(finite) // 4], finite[3 * len(finite) // 4]
                        spread = q3 - q1
                        if spread <= 0:
                            continue
                        low, high = q1 - 3 * spread, q3 + 3 * spread
                        outliers = [i for i, x in enumerate(floats) if not math.isfinite(x) or not low <= x <= high]
                        if len(outliers) == 1:
                            results.append({"byte_mask": spec, "reverse_bytes": reverse, "offset": offset,
                                            "float_format": endian + code, "count": n, "sane": sane,
                                            "q1": q1, "q3": q3, "outlier_index": outliers[0],
                                            "outlier_value": repr(floats[outliers[0]]),
                                            "prefix32_hex": value[:32].hex()})
    return results


def scan(source: str, mode: str) -> dict:
    if not re.fullmatch(r"[A-Z]+", source):
        raise ValueError("literal uppercase source required")
    seen, buffers = set(), set()
    paths = profiles = flagged = 0
    best, candidates = [], []
    for text, path in variants(source, mode):
        paths += 1
        digest = hashlib.sha256(text.encode()).digest()
        if digest in seen:
            continue
        seen.add(digest)
        for name, alphabet, bias in ALPHABETS:
            # Reversal of all bytes only permutes the lane labels, not this maximum.
            data = decode_base26(text, alphabet, bias)
            digest = hashlib.sha256(data).digest()
            if digest in buffers:
                continue
            buffers.add(digest)
            profile = bit_profile(data)
            profiles += 1
            record = {**path, "alphabet": name, "binary_sha256": digest.hex(), **profile}
            best.append(record)
            best = sorted(best, key=lambda r: -r["score"])[:8]
            if profile["score"] >= 8:
                flagged += 1
                candidates.append({**record, "numeric_candidates": numeric_candidates(data)[:64]})
    return {"mode": mode, "path_configurations": paths, "unique_letter_variants": len(seen),
            "binary_profiles": profiles, "flagged": flagged, "best_profiles": best,
            "flagged_records": candidates, "periods": list(PERIODS), "threshold": 8,
            "parity_masks": list(PARITY_MASKS),
            "letter_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "caution": "Structural screen only; unknown masking can erase bit bias. Threshold is not a p-value."}


def controls() -> list[dict]:
    rng = random.Random(314159)
    header = b"NACHTLORN" + struct.pack("<I", 640)
    values = [rng.gauss(0, 1) for _ in range(640)]
    values[431] = 37.0
    double = header + struct.pack("<640d", *values)
    single = header + struct.pack(">640f", *values)
    odd = header + b"".join(struct.pack("<I", rng.getrandbits(31) * 2 + 1) for _ in range(1280))
    cases = [double, apply_mask(double, {"kind": "xor", "key": "BLOOM", "phase": 3}),
             apply_mask(single, {"kind": "xor", "key": "NACHTLORN", "phase": 4}),
             apply_mask(odd, {"kind": "xor", "key": "NACHTLORN", "phase": 4})]
    result = [{"synthetic": True, "index": i, "profile": bit_profile(data)} for i, data in enumerate(cases)]
    assert all(r["profile"]["score"] >= 8 for r in result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path)
    parser.add_argument("--mode", choices=("periodic-then-route", "route-then-periodic"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--drop-final-i", action="store_true",
                        help="test a terminal literal I marker without editing the source")
    args = parser.parse_args(argv)
    if args.path.resolve() == args.output.resolve():
        parser.error("output must not overwrite source")
    raw = args.path.read_bytes()
    body = raw.decode("ascii").splitlines()[8:]
    if not body or any(not re.fullmatch(r" *[A-Z]+(?: +[A-Z]+)* *", row) for row in body):
        parser.error("invalid original body")
    source = "".join(c for row in body for c in row if "A" <= c <= "Z")
    original_count = len(source)
    if args.drop_final_i:
        if not source.endswith("I"):
            parser.error("terminal-I extraction requires an original final I")
        source = source[:-1]
    report = scan(source, args.mode)
    report["source_extraction"] = {"original_body_letters": original_count,
                                   "retained_body_letters": len(source),
                                   "removed_terminal": "I" if args.drop_final_i else ""}
    report["source_sha256"] = hashlib.sha256(raw).hexdigest()
    report["controls"] = controls()
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"paths": report["path_configurations"], "profiles": report["binary_profiles"],
                      "flagged": report["flagged"], "maximum_score": report["best_profiles"][0]["score"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
