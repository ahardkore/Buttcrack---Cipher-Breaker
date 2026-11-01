#!/usr/bin/env python3
"""R11/R12: separate replacement words, acrostics, and numeric digit alphabets."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.binary_envelope_probe import A26, keyed_alphabet  # noqa: E402
from scripts.nachtlorn_aead_probe import AES, MODES, Crypto, derive_keys, probe_packet  # noqa: E402
from scripts.nachtlorn_colour_byte_probe import LITERAL_WORDS, inspect  # noqa: E402
from scripts.nachtlorn_colour_byte_probe import scan as byte_scan  # noqa: E402
from scripts.nachtlorn_colour_probe import buffers, proposal, reference_contexts  # noqa: E402
from scripts.nachtlorn_colour_probe import scan as colour_scan  # noqa: E402
from scripts.nachtlorn_fieldwise_iblt_probe import encode_number  # noqa: E402

ALPHABET_KEYWORDS = ("BLOOM", "GLOOM", "WLOOM", "BLACK", "GREEN", "WHITE")


def reference_basis(raw: bytes, book: bytes) -> dict:
    content_passage = proposal(raw, book)["book_passage"]
    contexts = reference_contexts(book)["records"]
    black = [r for r in contexts if r["episode"] == 5 and "cold black marble bowl" in r["context"]
             and "mourning myself" in r["context"]]
    if len(black) != 1:
        raise ValueError("expected unique recorded black-bowl/mourning context")
    return {"green_white_passage": content_passage, "black_mourning_context": black[0],
            "caution": "Exploratory source grounding, not author-confirmed key assignments."}


def literal_roles(stream: str) -> dict:
    return {"hypothesis": "R11", "literal_word_reports": [colour_scan(stream, word) for word in LITERAL_WORDS],
            "direct_byte_xor": byte_scan(stream, LITERAL_WORDS),
            "caution": "Literal replacement words are candidate keys, not acrostics. Each key role is independent; no transformations are stacked."}


def _profile(values, allowed):
    values = tuple(values)
    if not values or len(set(values)) != len(values) or not set(values) <= set(allowed):
        raise ValueError("nonempty unique subset of the registered profile required")
    return values


def scan_keyword(stream: str, *, keywords=ALPHABET_KEYWORDS, password_words=LITERAL_WORDS) -> dict:
    if not re.fullmatch(r"[A-Z]+", stream) or len(stream) < 2:
        raise ValueError("literal uppercase source required")
    keywords, password_words = _profile(keywords, ALPHABET_KEYWORDS), _profile(password_words, LITERAL_WORDS)
    passwords = tuple(case for word in password_words for case in (word, word.lower(), word.title()))
    keys = derive_keys(passwords)
    seen, roundtrips, objects, diagnostics, authenticated = set(), [], [], [], []
    configurations, attempts, by_mode = 0, 0, {}
    for keyword in keywords:
        alphabet = keyed_alphabet(keyword)
        to_rank, to_glyph = str.maketrans(alphabet, A26), str.maketrans(A26, alphabet)
        for marker in (False, True):
            if marker and not stream.endswith("I"):
                continue
            text = stream[:-1] if marker else stream
            ranked = text.translate(to_rank)
            glyph_exact = ranked.translate(to_glyph) == text
            if not glyph_exact:
                raise ValueError("glyph mapping roundtrip failed")
            path = {"alphabet_keyword": keyword, "alphabet": alphabet, "drop_final_i": marker}
            verified_biases = set()
            for spec, data in buffers(ranked):
                bias = spec["bias"]
                if bias not in verified_biases:
                    value = int.from_bytes(data, spec["byteorder"])
                    rank = value - bias * ((26 ** len(text) - 1) // 25)
                    reconstructed = encode_number(rank, len(text)).translate(to_glyph)
                    numeric_exact = reconstructed + ("I" if marker else "") == stream
                    if not numeric_exact:
                        raise ValueError("numeric/glyph/source roundtrip failed")
                    roundtrips.append({**path, "bias": bias, "exact_glyph_roundtrip": glyph_exact,
                                       "exact_numeric_and_source_roundtrip": numeric_exact})
                    verified_biases.add(bias)
                configurations += 1
                digest = hashlib.sha256(data).hexdigest()
                if digest in seen:
                    continue
                seen.add(digest)
                packet_path = {**path, **spec, "binary_sha256": digest}
                direct = inspect(data)
                if direct["objects"]:
                    objects.append({**packet_path, "objects": direct["objects"], "decoded_hex": data.hex()})
                if direct["whole_printable_ascii_candidate"] or direct["unvalidated_origin_signatures"]:
                    diagnostics.append({**packet_path, **direct, "decoded_hex": data.hex()})
                if AES is None:
                    continue
                result = probe_packet(data, keys)
                attempts += result["attempts"]
                for mode, count in result["by_mode"].items():
                    by_mode[mode] = by_mode.get(mode, 0) + count
                for accepted in result["accepted"]:
                    authenticated.append({**packet_path, **accepted})
    return {"hypothesis": "R12", "source_letters": len(stream),
            "letter_sha256": hashlib.sha256(stream.encode()).hexdigest(),
            "alphabet_keywords": list(keywords), "password_words": list(password_words),
            "representation_configurations": configurations, "unique_buffers": len(seen),
            "roundtrips": roundtrips, "decoded_objects": objects, "diagnostic_candidates": diagnostics,
            "authentication_status": "tested" if AES is not None else "not_run_missing_optional_dependency",
            "crypto_version": Crypto.__version__ if Crypto is not None else None,
            "key_specification": [{k: v for k, v in row.items() if k != "key"} for row in keys],
            "modes": [list(pair) for pair in MODES], "tag_bytes": 16, "associated_data": "empty",
            "authentication_attempts": attempts, "attempts_by_mode": by_mode, "authenticated_packets": authenticated,
            "caution": "A declared digit-alphabet representation with at most one independent authenticated cipher, not a letterwise/XOR/encryption stack. Roundtrips do not validate plaintext. BLOOM direct decoding overlaps the historical baseline; colour-password combinations are explicit new inputs. Recovered numeric items and a final outlier are not assumed."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path)
    parser.add_argument("--book", type=Path, required=True)
    parser.add_argument("--mode", choices=("literal", "alphabet"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.resolve() in (args.path.resolve(), args.book.resolve()):
        parser.error("output must not overwrite either input")
    raw, book = args.path.read_bytes(), args.book.read_bytes()
    basis = reference_basis(raw, book)
    rows = raw.decode("ascii").splitlines()[8:]
    if not rows or any(not re.fullmatch(r" *[A-Z]+(?: +[A-Z]+)* *", row) for row in rows):
        parser.error("expected literal original body")
    stream = "".join(c for row in rows for c in row if "A" <= c <= "Z")
    report = literal_roles(stream) if args.mode == "literal" else scan_keyword(stream)
    report.update(source_sha256=hashlib.sha256(raw).hexdigest(), book_sha256=hashlib.sha256(book).hexdigest(),
                  reference_basis=basis)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    if args.mode == "literal":
        summary = {"words": [r["key"] for r in report["literal_word_reports"]],
                   "structured_objects": sum(len(r["literal_key_test"]["accepted_records"]) for r in report["literal_word_reports"]),
                   "authentication_attempts": sum(r["standalone_password_test"]["authentication_attempts"] for r in report["literal_word_reports"]),
                   "valid_tags": sum(len(r["standalone_password_test"]["accepted"]) for r in report["literal_word_reports"]),
                   "byte_xor_trials": report["direct_byte_xor"]["byte_xor_trials"],
                   "byte_xor_findings": len(report["direct_byte_xor"]["findings"])}
    else:
        summary = {key: len(report[key]) if isinstance(report[key], list) else report[key]
                   for key in ("representation_configurations", "unique_buffers", "decoded_objects", "diagnostic_candidates",
                               "authentication_status", "authentication_attempts", "authenticated_packets")}
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
