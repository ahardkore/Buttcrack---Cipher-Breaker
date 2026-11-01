#!/usr/bin/env python3
"""Probe binary envelopes after one clue-key periodic cipher and one route.

No intermediate-English pruning, source edits, pickle loading or recovered-code
execution. Two modes split the orderings into independent computational jobs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import zlib
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from buttcrack.ciphers.polyalphabetic import Porta  # noqa: E402
from buttcrack.ciphers.transposition import ColumnarTransposition, Myszkowski, RailFence  # noqa: E402
from scripts.binary_envelope_probe import (  # noqa: E402
    ALPHABETS,
    PACKINGS,
    SIGNATURES,
    ZLIB_HEADERS,
    decode_base26,
    inspect_binary,
)
from scripts.binary_text_probe import apply_mask, mask_specs, printable_prefix, text_candidate  # noqa: E402
from scripts.nachtlorn_state_packing import permutation, permute  # noqa: E402

KEYS = ("BLOOM", "BLPNM", "BLNPM", "NACHTLORN")


def periodic_specs() -> list[dict]:
    return [{"kind": "identity"}] + [
        {"kind": kind, "key": key, "phase": phase}
        for key in KEYS for phase in range(len(key))
        for kind in ("minus", "plus", "beaufort", "porta")]


def route_specs() -> list[dict]:
    return ([{"kind": "identity"}, {"kind": "reverse"}] +
            [{"kind": kind, "key": key} for kind in ("columnar", "myszkowski") for key in KEYS] +
            [{"kind": "rail", "rails": rails} for rails in range(2, 9)] +
            [{"kind": "shuffle", "unit": unit, "indent_draws": draws, "inverse": inverse}
             for unit in (1, 5, 60) for draws in (0, 146) for inverse in (False, True)])


def apply_periodic(text: str, spec: dict, *, inverse: bool = False) -> str:
    kind = spec["kind"]
    if kind == "identity":
        return text
    key, phase = spec["key"], spec["phase"]
    key = key[phase:] + key[:phase]
    if kind == "porta":
        return Porta().decrypt(text, key)
    if inverse and kind in ("minus", "plus"):
        kind = "plus" if kind == "minus" else "minus"
    if kind == "minus":
        return "".join(chr(65 + (ord(c) - ord(key[i % len(key)])) % 26) for i, c in enumerate(text))
    if kind == "plus":
        return "".join(chr(65 + (ord(c) + ord(key[i % len(key)]) - 130) % 26) for i, c in enumerate(text))
    if kind == "beaufort":
        return "".join(chr(65 + (ord(key[i % len(key)]) - ord(c)) % 26) for i, c in enumerate(text))
    raise ValueError("unknown periodic operation")


@lru_cache(maxsize=64)
def shuffle_indices(length: int, unit: int, draws: int) -> tuple[int, ...]:
    return tuple(permutation(length, unit, draws))


def apply_route(text: str, spec: dict, *, inverse: bool = False) -> str:
    kind = spec["kind"]
    if kind == "identity":
        return text
    if kind == "reverse":
        return text[::-1]
    if kind == "shuffle":
        return permute(text, spec["unit"], shuffle_indices(len(text), spec["unit"], spec["indent_draws"]),
                       inverse=bool(spec["inverse"]) != inverse)
    cipher, key = ({"columnar": ColumnarTransposition, "myszkowski": Myszkowski, "rail": RailFence}[kind](),
                   spec.get("key", spec.get("rails")))
    return cipher.encrypt(text, key) if inverse else cipher.decrypt(text, key)


def variants(source: str, mode: str):
    if mode == "periodic-then-route":
        for periodic in periodic_specs():
            first = apply_periodic(source, periodic)
            for route in route_specs():
                yield apply_route(first, route), {"periodic": periodic, "route": route}
    elif mode == "route-then-periodic":
        # Identity cases already occur in the other job.
        for route in route_specs()[1:]:
            first = apply_route(source, route)
            for periodic in periodic_specs()[1:]:
                yield apply_periodic(first, periodic), {"periodic": periodic, "route": route}
    else:
        raise ValueError("unknown operation order")


def book_dictionaries(raw: bytes) -> tuple[dict[int, bytes], list[dict]]:
    letters = re.sub(rb"[^A-Za-z]", b"", raw).upper()
    variants = (("original-utf8", raw), ("original-last32768", raw[-32768:]),
                ("ascii-letters-upper", letters), ("ascii-letters-upper-last32768", letters[-32768:]))
    dictionaries, metadata = {}, []
    for name, data in variants:
        identifier = zlib.adler32(data)
        if identifier in dictionaries and dictionaries[identifier] != data:
            raise ValueError("preset dictionary checksum collision")
        dictionaries[identifier] = data
        metadata.append({"name": name, "bytes": len(data), "adler32": f"{identifier:08x}",
                         "sha256": hashlib.sha256(data).hexdigest()})
    return dictionaries, metadata


def single_stage_variants(source: str):
    for periodic in periodic_specs():
        yield apply_periodic(source, periodic), {"periodic": periodic, "route": {"kind": "identity"}}
    for route in route_specs()[1:]:
        yield apply_route(source, route), {"periodic": {"kind": "identity"}, "route": route}


def byte_prefix_plausible(data: bytes) -> bool:
    return (printable_prefix(data) or bool(ZLIB_HEADERS.match(data)) or
            any(data.startswith(magic) for magic in SIGNATURES.values()) or
            len(data) >= 2 and data[0] == 128 and data[1] <= 5)


def scan_byte_layer(source: str, dictionaries: dict[int, bytes] | None = None,
                    byte_keys: tuple[str, ...] | None = None) -> dict:
    letters_seen, buffers_seen = set(), set()
    paths = decodes = invalid = mask_cases = selected = attempts = verified_count = text_count = 0
    dictionary_requests = dictionary_matches = 0
    verified, texts, headers = [], [], []
    masks = mask_specs(KEYS if byte_keys is None else byte_keys)
    for text, path in single_stage_variants(source):
        paths += 1
        digest = hashlib.sha256(text.encode()).digest()
        if digest in letters_seen:
            continue
        letters_seen.add(digest)
        for alphabet_name, alphabet, bias in ALPHABETS:
            for width, byte_width in PACKINGS:
                for byteorder in ("big", "little"):
                    try:
                        data = decode_base26(text, alphabet, bias, width, byte_width, byteorder)
                    except ValueError:
                        invalid += 1
                        continue
                    decodes += 1
                    digest = hashlib.sha256(data).digest()
                    if digest in buffers_seen:
                        continue
                    buffers_seen.add(digest)
                    for mask in masks:
                        mask_cases += 1
                        prefix = apply_mask(data[:128], mask)
                        if not byte_prefix_plausible(prefix):
                            continue
                        selected += 1
                        decoded = apply_mask(data, mask)
                        metadata = {**path, "alphabet": alphabet_name, "block_width": width,
                                    "byte_width": byte_width, "byteorder": byteorder, "byte_mask": mask,
                                    "binary_sha256": hashlib.sha256(decoded).hexdigest()}
                        candidate = text_candidate(decoded)
                        if candidate is not None:
                            text_count += 1
                            if len(texts) < 32:
                                texts.append({**metadata, "text": candidate})
                        result = inspect_binary(decoded, dictionaries)
                        attempts += result["compression_attempts"]
                        dictionary_requests += result["dictionary_requests"]
                        dictionary_matches += result["dictionary_id_matches"]
                        verified_count += len(result["verified"])
                        if result["verified"] and len(verified) < 32:
                            verified.append({**metadata, "objects": result["verified"]})
                        if result["signature_headers"] and len(headers) < 1024:
                            headers.append({**metadata, "headers": result["signature_headers"]})
    return {
        "status": "Bounded byte-layer test; printability is not a verified answer.",
        "mode": "byte-layer", "source_letters": len(source),
        "letter_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "path_configurations": paths, "unique_letter_variants": len(letters_seen),
        "valid_binary_decodings": decodes, "invalid_packed_decodings": invalid,
        "unique_binary_buffers": len(buffers_seen), "byte_mask_configurations": mask_cases,
        "prefix_selected": selected, "wrapped_compression_attempts": attempts,
        "zlib_dictionary_requests": dictionary_requests, "preset_dictionary_id_matches": dictionary_matches,
        "verified_object_count": verified_count, "verified_records": verified,
        "text_candidate_count": text_count, "text_candidates": texts, "header_examples": headers,
        "specification": {"letter_stage": "identity or ONE periodic operation or ONE route",
                          "periodic_operations": periodic_specs(), "routes": route_specs(),
                          "byte_masks": masks,
                          "alphabets": [{"name": n, "alphabet": a, "bias": b} for n, a, b in ALPHABETS],
                          "packings": [list(pair) for pair in PACKINGS], "byteorders": ["big", "little"],
                          "prefilter": "first128 bytes: UTF8/90percent printable or an object header at zero",
                          "text_test": "complete UTF8, at least64 characters, at least98percent printable",
                          "preset_dictionary_ids": [f"{i:08x}" for i in (dictionaries or {})],
                          "compression_output_limit": 1048576, "lzma_memory_limit": 67108864},
        "caution": "No arbitrary byte keys, prefix offsets, or two-letter-operation-plus-byte-mask combinations tested.",
    }


def scan(source: str, mode: str, dictionaries: dict[int, bytes] | None = None,
         *, byte_keys: tuple[str, ...] | None = None) -> dict:
    if not re.fullmatch(r"[A-Z]+", source):
        raise ValueError("literal uppercase ASCII source required")
    if byte_keys is not None and mode != "byte-layer":
        raise ValueError("byte keys apply only to byte-layer mode")
    if mode == "byte-layer":
        return scan_byte_layer(source, dictionaries, byte_keys)
    letter_seen, binary_seen = set(), set()
    paths = decodes = invalid = duplicate_bytes = attempts = verified_total = headers_total = 0
    header_examples, verified = [], []
    dictionary_requests = dictionary_matches = 0
    for text, path in variants(source, mode):
        paths += 1
        digest = hashlib.sha256(text.encode()).digest()
        if digest in letter_seen:
            continue
        letter_seen.add(digest)
        for alphabet_name, alphabet, bias in ALPHABETS:
            for width, byte_width in PACKINGS:
                for byteorder in ("big", "little"):
                    try:
                        data = decode_base26(text, alphabet, bias, width, byte_width, byteorder)
                    except ValueError:
                        invalid += 1
                        continue
                    decodes += 1
                    binary_digest = hashlib.sha256(data).digest()
                    if binary_digest in binary_seen:
                        duplicate_bytes += 1
                        continue
                    binary_seen.add(binary_digest)
                    result = inspect_binary(data, dictionaries)
                    attempts += result["compression_attempts"]
                    dictionary_requests += result["dictionary_requests"]
                    dictionary_matches += result["dictionary_id_matches"]
                    headers_total += len(result["signature_headers"])
                    metadata = {**path, "alphabet": alphabet_name, "block_width": width,
                                "byte_width": byte_width, "byteorder": byteorder,
                                "decoded_bytes": len(data), "binary_sha256": binary_digest.hex()}
                    if result["verified"]:
                        verified_total += len(result["verified"])
                        if len(verified) < 32:
                            verified.append({**metadata, "objects": result["verified"]})
                    if result["signature_headers"] and len(header_examples) < 1024:
                        header_examples.append({**metadata, "headers": result["signature_headers"]})
    return {
        "status": "Binary-envelope construction test, not an assumed solution.",
        "mode": mode, "source_letters": len(source),
        "letter_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "path_configurations": paths, "unique_letter_variants": len(letter_seen),
        "valid_binary_decodings": decodes, "invalid_packed_decodings": invalid,
        "duplicate_binary_decodings": duplicate_bytes, "unique_binary_buffers": len(binary_seen),
        "wrapped_compression_attempts": attempts, "verified_object_count": verified_total,
        "zlib_dictionary_requests": dictionary_requests, "preset_dictionary_id_matches": dictionary_matches,
        "verified_records": verified, "verified_record_limit": 32,
        "magic_headers_recorded": headers_total, "header_examples": header_examples,
        "header_record_limit": 1024,
        "specification": {"periodic_operations": periodic_specs(), "routes": route_specs(),
                          "alphabets": [{"name": name, "alphabet": alphabet, "bias": bias}
                                        for name, alphabet, bias in ALPHABETS],
                          "packings": [list(pair) for pair in PACKINGS],
                          "byteorders": ["big", "little"], "compression_output_limit": 1048576,
                          "lzma_memory_limit": 67108864,
                          "pickle_policy": "static syntax only; never load or execute",
                          "archive_policy": "bounded reads only; never extract",
                          "preset_dictionary_ids": [f"{identifier:08x}" for identifier in (dictionaries or {})]},
        "caution": "Tests only these letter transforms and binary wrappers; magic headers alone are not verified objects.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path)
    parser.add_argument("--mode", choices=("periodic-then-route", "route-then-periodic", "byte-layer"), required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--drop-final-i", action="store_true",
                        help="test a terminal literal I marker outside the encoded body; source is never edited")
    parser.add_argument("--byte-key-case", choices=("upper", "lower", "both"), default="upper",
                        help="ASCII XOR key case in byte-layer mode (default: upper)")
    parser.add_argument("--dictionary", type=Path, help="optional book bytes for four preset-dictionary variants")
    args = parser.parse_args(argv)
    if args.output and args.output.resolve() == args.path.resolve():
        parser.error("output must not overwrite source")
    if args.output and args.dictionary and args.output.resolve() == args.dictionary.resolve():
        parser.error("output must not overwrite dictionary")
    started = time.monotonic()
    try:
        raw = args.path.read_bytes()
        body = raw.decode("ascii").splitlines()[8:]
        if not body or any(not re.fullmatch(r" *[A-Z]+(?: +[A-Z]+)* *", row) for row in body):
            raise ValueError("expected original body beginning at line9")
        source = "".join(c for row in body for c in row if "A" <= c <= "Z")
        original_count = len(source)
        if args.drop_final_i:
            if not source.endswith("I"):
                raise ValueError("terminal-I extraction requires an original final I")
            source = source[:-1]
        extraction = {"original_body_letters": original_count, "retained_body_letters": len(source),
                      "removed_terminal": "I" if args.drop_final_i else ""}
        dictionaries, dictionary_metadata = book_dictionaries(args.dictionary.read_bytes()) if args.dictionary else (None, [])
        byte_keys = None if args.byte_key_case == "upper" else (
            tuple(k.lower() for k in KEYS) if args.byte_key_case == "lower" else
            KEYS + tuple(k.lower() for k in KEYS))
        report = scan(source, args.mode, dictionaries, byte_keys=byte_keys)
        report["dictionary_variants"] = dictionary_metadata
        report["source_extraction"] = extraction
        report["source_sha256"] = hashlib.sha256(raw).hexdigest()
        report["elapsed_seconds"] = time.monotonic() - started
    except (OSError, ValueError, UnicodeError) as error:
        parser.error(str(error))
    serialized = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(serialized)
        print(json.dumps({key: report[key] for key in
                          ("path_configurations", "unique_letter_variants", "unique_binary_buffers",
                           "verified_object_count", "wrapped_compression_attempts", "elapsed_seconds")}))
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
