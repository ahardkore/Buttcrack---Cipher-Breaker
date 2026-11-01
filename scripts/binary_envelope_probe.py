#!/usr/bin/env python3
"""Read-only base-26 binary decoding and bounded envelope inspection.

No eval, exec, pickle.load(s), archive extraction, or recovered-code execution.
Compression must reach a checksum-validated EOF within the output cap. A magic
header alone is recorded separately and is never a verified recovery.
"""
from __future__ import annotations

import bz2
import hashlib
import io
import json
import lzma
import pickletools
import re
import zipfile
import zlib
from functools import lru_cache

A26 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIGITS = "0123456789abcdefghijklmnop"
OUTPUT_LIMIT = 1024 * 1024
LZMA_MEMORY_LIMIT = 64 * 1024 * 1024


def keyed_alphabet(key: str) -> str:
    return "".join(dict.fromkeys(key + A26))


ALPHABETS = (
    ("A0", A26, 0), ("A1-bijective", A26, 1),
    ("I0", A26[8:] + A26[:8], 0), ("reverse", A26[::-1], 0),
    ("keyed-BLOOM", keyed_alphabet("BLOOM"), 0),
    ("keyed-NACHTLORN", keyed_alphabet("NACHTLORN"), 0),
)
PACKINGS = ((None, None), (5, 3), (7, 4), (14, 8))


@lru_cache(maxsize=128)
def geometric(width: int) -> int:
    return (26 ** width - 1) // 25


@lru_cache(maxsize=16)
def digit_table(alphabet: str) -> dict:
    if len(alphabet) != 26 or set(alphabet) != set(A26):
        raise ValueError("alphabet must permute the26 uppercase ASCII letters")
    return str.maketrans(alphabet, DIGITS)


def parse_digits(digits: str, bias: int = 0) -> int:
    """Chunked native parsing avoids changing Python's global int-string limit."""
    value = 0
    for start in range(0, len(digits), 512):
        chunk = digits[start:start + 512]
        value = value * (26 ** len(chunk)) + int(chunk, 26)
    return value + bias * geometric(len(digits))


def decode_base26(text: str, alphabet: str = A26, bias: int = 0,
                  block_width: int | None = None, byte_width: int | None = None,
                  byteorder: str = "big") -> bytes:
    """Whole integers use minimal bytes; leading zero-byte count is unknowable.

    Packed full blocks use fixed byte widths. A short final block is retained
    as a minimal, at-least-one-byte integer; it is never dropped as padding.
    """
    if not re.fullmatch(r"[A-Z]+", text) or bias not in (0, 1) or byteorder not in ("big", "little"):
        raise ValueError("literal uppercase text, bias0/1 and a valid byte order required")
    digits = text.translate(digit_table(alphabet))
    if block_width is None:
        if byte_width is not None:
            raise ValueError("byte width requires a block width")
        value = parse_digits(digits, bias)
        return value.to_bytes(max(1, (value.bit_length() + 7) // 8), byteorder)
    if block_width < 1 or byte_width is None or byte_width < 1:
        raise ValueError("positive block/byte widths required")
    out = bytearray()
    for start in range(0, len(digits), block_width):
        block = digits[start:start + block_width]
        value = parse_digits(block, bias)
        size = byte_width if len(block) == block_width else max(1, (value.bit_length() + 7) // 8)
        try:
            out.extend(value.to_bytes(size, byteorder))
        except OverflowError as error:
            raise ValueError("packed integer exceeds the declared byte width") from error
    return bytes(out)


def reject_constant(value: str):
    raise ValueError(f"non-JSON constant: {value}")


def describe(data: bytes) -> dict:
    """Recognize complete JSON or statically parse a complete binary pickle."""
    summary = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    if len(data) > OUTPUT_LIMIT:
        return {**summary, "kind": "over-limit"}
    prefix = data.lstrip()[:1]
    if prefix in (b"{", b"[", b'"', b"t", b"f", b"n", b"-") or prefix.isdigit():
        try:
            value = json.loads(data.decode("utf-8"), parse_constant=reject_constant)
            return {**summary, "kind": "json", "type": type(value).__name__,
                    "items": len(value) if isinstance(value, (dict, list, str)) else None,
                    "preview": repr(value)[:240]}
        except (ValueError, UnicodeError, RecursionError):
            pass
    if len(data) >= 2 and data[0] == 0x80 and data[1] <= 5:
        try:
            count = 0
            last = None
            dangerous = False
            for operation, _, position in pickletools.genops(data):
                count += 1
                last = operation.name, position
                dangerous |= operation.name in {
                    "GLOBAL", "STACK_GLOBAL", "REDUCE", "BUILD", "OBJ", "INST", "NEWOBJ", "NEWOBJ_EX",
                }
            if last == ("STOP", len(data) - 1):
                return {**summary, "kind": "pickle-static-only", "opcodes": count,
                        "executable_opcodes_present": dangerous,
                        "caution": "Syntax parsed only; object not loaded and semantics not validated."}
        except (ValueError, OverflowError, UnicodeError, RecursionError, EOFError):
            pass
    return {**summary, "kind": "unclassified-bytes"}


# Valid DEFLATE/zlib CMF/FLG pairs, including headers requesting a dictionary.
# Consume only CMF, checking FLG with lookahead: adjacent valid headers may overlap.
ZLIB_HEADERS = re.compile(b"|".join(
    re.escape(bytes((cmf,))) + b"(?=[" + b"".join(
        re.escape(bytes((flag,))) for flag in range(256)
        if (cmf * 256 + flag) % 31 == 0) + b"])"
    for cmf in range(8, 121, 16)
))
SIGNATURES = {
    "png": b"\x89PNG\r\n\x1a\n", "pdf": b"%PDF-", "gif87": b"GIF87a", "gif89": b"GIF89a",
    "jpeg": b"\xff\xd8\xff", "npy": b"\x93NUMPY", "sqlite": b"SQLite format 3\x00",
    "zip": b"PK\x03\x04", "gzip": b"\x1f\x8b\x08", "bzip2": b"BZh", "xz": b"\xfd7zXZ\x00",
}


def decompress_member(data: bytes, kind: str, limit: int = OUTPUT_LIMIT,
                      dictionary: bytes | None = None) -> tuple[bytes, int] | None:
    """Return output and consumed input only after bounded, validated EOF."""
    if limit < 1:
        raise ValueError("positive output limit required")
    try:
        if kind in ("gzip", "zlib"):
            decoder = (zlib.decompressobj(15, zdict=dictionary) if kind == "zlib" and dictionary is not None
                       else zlib.decompressobj(31 if kind == "gzip" else 15))
        elif kind == "bzip2":
            decoder = bz2.BZ2Decompressor()
        elif kind == "xz":
            decoder = lzma.LZMADecompressor(memlimit=LZMA_MEMORY_LIMIT)
        else:
            raise ValueError("unknown compression kind")
        output = decoder.decompress(data, limit + 1)
        if len(output) > limit or not decoder.eof:
            return None
        return output, len(data) - len(decoder.unused_data)
    except (zlib.error, lzma.LZMAError, OSError, EOFError, ValueError, OverflowError):
        return None


def inspect_binary(data: bytes, dictionaries: dict[int, bytes] | None = None) -> dict:
    """Inspect full objects and embedded wrapped streams; never execute data."""
    verified, signatures = [], []
    classification = describe(data)
    if classification["kind"] in ("json", "pickle-static-only"):
        verified.append({"format": classification["kind"], "offset": 0,
                         "classification": classification})
    starts = set()
    for kind, magic in SIGNATURES.items():
        start = 0
        while (offset := data.find(magic, start)) >= 0:
            if len(signatures) < 32:
                signatures.append({"format": kind, "offset": offset})
            if kind in ("gzip", "bzip2", "xz"):
                starts.add((kind, offset))
            start = offset + 1
    for match in ZLIB_HEADERS.finditer(data):
        starts.add(("zlib", match.start()))
    attempts = len(starts)
    dictionary_requests = dictionary_matches = 0
    for kind, offset in sorted(starts):
        dictionary = None
        if kind == "zlib" and len(data) >= offset + 6 and data[offset + 1] & 32:
            dictionary_requests += 1
            dictionary_id = int.from_bytes(data[offset + 2:offset + 6], "big")
            dictionary = (dictionaries or {}).get(dictionary_id)
            dictionary_matches += dictionary is not None
        result = decompress_member(data[offset:], kind, dictionary=dictionary)
        if result is not None:
            output, consumed = result
            verified.append({"format": kind, "offset": offset, "compressed_bytes": consumed,
                             "trailing_bytes": len(data) - offset - consumed,
                             "dictionary_adler32": f"{dictionary_id:08x}" if dictionary is not None else None,
                             "classification": describe(output)})
    if any(s["format"] == "zip" for s in signatures):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                infos = archive.infolist()
                if (len(infos) <= 128 and sum(i.file_size for i in infos) <= OUTPUT_LIMIT
                        and not any(i.flag_bits & 1 for i in infos)):
                    members = []
                    for info in infos:
                        with archive.open(info) as member:
                            content = member.read(OUTPUT_LIMIT + 1)
                        if len(content) != info.file_size:
                            raise ValueError("incomplete archive member")
                        members.append({"name": info.filename, "classification": describe(content)})
                    verified.append({"format": "zip", "offset": 0, "members": members})
        except (zipfile.BadZipFile, ValueError, OSError, RuntimeError, NotImplementedError,
                zlib.error, lzma.LZMAError, EOFError):
            pass
    return {"verified": verified, "signature_headers": signatures, "compression_attempts": attempts,
            "dictionary_requests": dictionary_requests, "dictionary_id_matches": dictionary_matches}
