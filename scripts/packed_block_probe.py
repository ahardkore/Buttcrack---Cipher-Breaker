#!/usr/bin/env python3
"""Test seeded, base-26 whole-block filler behind fixed phase alphabets.

Unlike drawing one letter at a time, these models draw an integer for an entire
block, then expand its base-26 digits. A matching unaltered prefix is required.
Mappings are learned only from the training prefix; predictions for the rest
are held out. This is a bounded construction test, not an English-word search.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import time
from functools import lru_cache
from pathlib import Path

WIDTHS = (2, 3, 4, 5, 6, 10, 12, 20, 26, 30, 60, 3660, 5076, 8736)
METHODS = ("randrange", "bits-mod", "float-scaled", "rational53")
ORDERS = ("big", "little")


@lru_cache(maxsize=128)
def power26(width: int) -> int:
    return 26 ** width


def block_letters(rng: random.Random, width: int, method: str, order: str, count: int) -> str:
    """Draw full-width blocks and clip the last one; leading zero digits are A.

    rational53 is floor(U53 * 26**width / 2**53), not floating multiplication.
    float-scaled is literally int(random() * 26**width), including rounding.
    """
    if width < 1 or count < 1 or method not in METHODS or order not in ORDERS:
        raise ValueError("positive width/count and a declared method/order are required")
    if method == "float-scaled" and width > 217:
        raise ValueError("native float-scaled bounds overflow above width217")
    bound = power26(width)
    result = []
    remaining = count
    while remaining:
        if method == "randrange":
            value = rng.randrange(bound)
        elif method == "bits-mod":
            value = rng.getrandbits(bound.bit_length()) % bound
        elif method == "float-scaled":
            value = int(rng.random() * bound)
        else:
            u53 = (rng.getrandbits(27) << 26) | rng.getrandbits(26)
            value = (u53 * bound) >> 53
        take = min(width, remaining)
        if order == "big":
            value //= power26(width - take)
        digits = []
        for _ in range(take):
            value, digit = divmod(value, 26)
            digits.append(chr(65 + digit))
        result.extend(reversed(digits) if order == "big" else digits)
        remaining -= take
    return "".join(result)


def phase_maps(source: str, carrier: str, phases: int = 5) -> list[dict[str, str]] | None:
    """Infer carrier→source bijections; None means a conflict in supplied data."""
    if phases < 1 or len(source) != len(carrier):
        raise ValueError("positive phase count and equal-length strings required")
    maps, inverse = [{} for _ in range(phases)], [{} for _ in range(phases)]
    for i, (actual, generated) in enumerate(zip(source, carrier)):
        phase = i % phases
        if (generated in maps[phase] and maps[phase][generated] != actual or
                actual in inverse[phase] and inverse[phase][actual] != generated):
            return None
        maps[phase][generated] = actual
        inverse[phase][actual] = generated
    return maps


def predict(carrier: str, maps: list[dict[str, str]]) -> str:
    """A missing training symbol remains unknown, never filled from held-out data."""
    if not maps:
        raise ValueError("at least one phase map required")
    return "".join(maps[i % len(maps)].get(c, "?") for i, c in enumerate(carrier))


def scan(source: str, seeds: list[int | str], *, widths: tuple[int, ...] = WIDTHS,
         offset_max: int = 1024, prefix: int = 120, train: int = 3000) -> dict:
    """Offsets count raw 32-bit MT words before the first whole-block draw."""
    if not re.fullmatch(r"[A-Z]+", source):
        raise ValueError("source must contain uppercase ASCII letters only")
    if not seeds or not widths or any(w < 1 for w in widths):
        raise ValueError("nonempty seeds and positive widths required")
    if offset_max < 0 or not 1 <= prefix <= train < len(source):
        raise ValueError("require nonnegative offset and 1 <= prefix <= train < source length")
    count = prefix_hits = training_fits = 0
    records = []
    for seed in seeds:
        base = random.Random(seed)
        states = []
        for _ in range(offset_max + 1):
            states.append(base.getstate())
            base.getrandbits(32)
        rng = random.Random(0)
        for width in widths:
            for method in METHODS:
                if method == "float-scaled" and width > 217:
                    continue
                for order in ORDERS:
                    for offset, state in enumerate(states):
                        count += 1
                        rng.setstate(state)
                        generated = block_letters(rng, width, method, order, prefix)
                        if phase_maps(source[:prefix], generated) is None:
                            continue
                        prefix_hits += 1
                        rng.setstate(state)
                        carrier = block_letters(rng, width, method, order, len(source))
                        maps = phase_maps(source[:train], carrier[:train])
                        if maps is None:
                            continue
                        training_fits += 1
                        prediction = predict(carrier, maps)
                        mismatches = [i for i in range(train, len(source))
                                      if prediction[i] != "?" and prediction[i] != source[i]]
                        unknown = sum(c == "?" for c in prediction[train:])
                        if len(records) < 32:
                            records.append({
                                "seed": seed, "width": width, "method": method,
                                "order": order, "raw_word_offset": offset,
                                "phase_maps": maps, "heldout_letters": len(source) - train,
                                "heldout_unknown": unknown,
                                "heldout_mismatch_count": len(mismatches),
                                "mismatch_positions": mismatches,
                                "prediction_sha256": hashlib.sha256(prediction.encode()).hexdigest(),
                            })
    return {
        "specification": {"seeds": seeds, "widths": list(widths), "methods": list(METHODS),
                          "orders": list(ORDERS), "raw_word_offsets": [0, offset_max],
                          "unaltered_prefix": prefix, "training_letters": train,
                          "independent_phase_alphabets": 5,
                          "float_width_limit": 217, "last_block": "full draw then clip"},
        "letters": len(source), "letter_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "cases": count, "prefix_matches": prefix_hits, "training_fits": training_fits,
        "prediction_records": records, "prediction_record_limit": 32,
        "caution": "Requires an unaltered prefix; tests only the listed seeds, block APIs, offsets and five fixed phase alphabets.",
    }


def controls() -> list[dict]:
    """Search four unknown constructions; truth is used only after training."""
    results = []
    marker = "FINDTHEODDOBJECT"
    for index, (width, method, order, offset) in enumerate((
            (60, "randrange", "big", 17), (5, "bits-mod", "little", 23),
            (26, "float-scaled", "big", 31), (12, "rational53", "little", 7))):
        rng = random.Random(4300)
        for _ in range(offset):
            rng.getrandbits(32)
        carrier = block_letters(rng, width, method, order, 8736)
        key_rng = random.Random(271828 + index)
        maps = []
        for _ in range(5):
            alphabet = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            key_rng.shuffle(alphabet)
            maps.append(dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", alphabet)))
        truth = predict(carrier, maps)
        start = 5000
        while truth[start] == marker[0] or truth[start + len(marker) - 1] == marker[-1]:
            start += 1
        source = truth[:start] + marker + truth[start + len(marker):]
        expected = [i for i in range(3000, len(source)) if source[i] != truth[i]]
        report = scan(source, [4300], widths=(5, 12, 26, 60), offset_max=32)
        # Select a prediction class using training compatibility, not held-out truth.
        # Initial rejected randrange draws can give different offsets the same stream.
        winners = report["prediction_records"]
        prediction_classes = {r["prediction_sha256"] for r in winners}
        passed = (report["training_fits"] == len(winners) > 0 and
                  len(prediction_classes) == 1)
        if passed:
            winner = winners[0]
            known_model_present = any((r["width"], r["method"], r["order"],
                                       r["raw_word_offset"]) == (width, method, order, offset)
                                      for r in winners)
            passed = (known_model_present and winner["heldout_unknown"] == 0 and
                      winner["mismatch_positions"] == expected and
                      winner["prediction_sha256"] == hashlib.sha256(truth.encode()).hexdigest())
        results.append({"synthetic": True, "width": width, "method": method,
                        "order": order, "raw_word_offset": offset,
                        "marker": marker, "marker_start": start,
                        "heldout_letters": 5736, "expected_mismatches": len(expected),
                        "search_cases": report["cases"],
                        "training_fits": report["training_fits"],
                        "training_prediction_classes": len(prediction_classes),
                        "compatible_raw_word_offsets": sorted({r["raw_word_offset"] for r in winners}),
                        "passed": passed})
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path)
    parser.add_argument("--seed-int", action="append", type=int, default=[])
    parser.add_argument("--seed-text", action="append", default=[])
    parser.add_argument("--offset-max", type=int, default=1024)
    parser.add_argument("--width", action="append", type=int, help="override the default block widths")
    parser.add_argument("--controls", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.output and args.output.resolve() == args.path.resolve():
        parser.error("output must not overwrite the source")
    started = time.monotonic()
    try:
        raw = args.path.read_bytes()
        body = raw.decode("ascii").splitlines()[8:]
        if not body or any(not re.fullmatch(r" *[A-Z]+(?: +[A-Z]+)* *", row) for row in body):
            raise ValueError("expected original uppercase body beginning at line9")
        source = "".join(c for row in body for c in row if "A" <= c <= "Z")
        seeds = args.seed_int + args.seed_text or [4300]
        report = scan(source, seeds, widths=tuple(args.width) if args.width else WIDTHS,
                      offset_max=args.offset_max)
        report["source_sha256"] = hashlib.sha256(raw).hexdigest()
        if args.controls:
            report["synthetic_controls"] = controls()
            if not all(c["passed"] for c in report["synthetic_controls"]):
                raise ValueError("a synthetic control failed")
        report["elapsed_seconds"] = time.monotonic() - started
    except (OSError, ValueError, UnicodeError) as error:
        parser.error(str(error))
    serialized = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(serialized)
        print(json.dumps({key: report[key] for key in
                          ("cases", "prefix_matches", "training_fits", "elapsed_seconds")}))
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
