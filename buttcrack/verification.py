"""Exact, human-readable round-trip verification helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class VerificationResult:
    exact: bool
    expected: str
    produced: str
    mismatch_index: int | None
    message: str


def round_trip(
    plaintext: str,
    ciphertext: str,
    encrypt: Callable[[str], str],
    *,
    normalizer: Callable[[str], str] | None = None,
) -> VerificationResult:
    """Compare an encryption result and report the first mismatch clearly."""
    normalize = normalizer or (lambda value: value)
    expected = normalize(ciphertext)
    produced = normalize(encrypt(plaintext))
    limit = min(len(expected), len(produced))
    mismatch = next((i for i in range(limit) if expected[i] != produced[i]), None)
    if mismatch is None and len(expected) != len(produced):
        mismatch = limit
    if mismatch is None:
        return VerificationResult(True, expected, produced, None, "exact round trip")
    if mismatch >= limit:
        detail = f"length mismatch: expected {len(expected)}, produced {len(produced)}"
    else:
        detail = f"mismatch at position {mismatch}: expected {expected[mismatch]!r}, produced {produced[mismatch]!r}"
    return VerificationResult(False, expected, produced, mismatch, detail)
