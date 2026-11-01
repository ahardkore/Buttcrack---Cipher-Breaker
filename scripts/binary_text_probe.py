"""Language-independent text candidates and clue-key byte transforms.

Printability suggests inspection, not a verified solution. These functions never
execute or deserialize recovered code and never silently drop input bytes.
"""
from __future__ import annotations

import codecs
import hashlib
from functools import lru_cache


def printable_fraction(text: str) -> float:
    return sum(c.isprintable() or c in "\r\n\t" for c in text) / len(text) if text else 0.0


def text_candidate(data: bytes, minimum_chars: int = 64) -> dict | None:
    try:
        text = data.decode("utf-8")
    except UnicodeError:
        return None
    if len(text) < minimum_chars or printable_fraction(text) < 0.98:
        return None
    return {"kind": "utf8-text-candidate", "bytes": len(data), "characters": len(text),
            "sha256": hashlib.sha256(data).hexdigest(), "preview": text[:500],
            "caution": "Language-independent text candidate, not a verified answer."}


def printable_prefix(data: bytes) -> bool:
    """Allow a partial final UTF-8 character in the128-byte prefilter."""
    try:
        text = codecs.getincrementaldecoder("utf-8")().decode(data[:128], final=False)
    except UnicodeError:
        return False
    return bool(text) and printable_fraction(text) >= 0.90


def mask_specs(keys: tuple[str, ...]) -> list[dict]:
    return ([{"kind": "identity"}] +
            [{"kind": "xor", "key": key, "phase": phase}
             for key in keys for phase in range(len(key))] +
            [{"kind": "add", "amount": 1}, {"kind": "add", "amount": -1}])


@lru_cache(maxsize=32)
def xor_table(value: int) -> bytes:
    return bytes(i ^ value for i in range(256))


def apply_mask(data: bytes, spec: dict, *, inverse: bool = False) -> bytes:
    kind = spec["kind"]
    if kind == "identity":
        return data
    if kind == "add":
        amount = spec["amount"] * (-1 if inverse else 1)
        return data.translate(bytes((i + amount) % 256 for i in range(256)))
    if kind == "xor":
        key = spec["key"].encode("ascii")
        phase = spec["phase"]
        if not key or not 0 <= phase < len(key):
            raise ValueError("nonempty ASCII key and in-range phase required")
        key = key[phase:] + key[:phase]
        out = bytearray(len(data))
        for offset, value in enumerate(key):
            out[offset::len(key)] = data[offset::len(key)].translate(xor_table(value))
        return bytes(out)
    raise ValueError("unknown byte transform")
