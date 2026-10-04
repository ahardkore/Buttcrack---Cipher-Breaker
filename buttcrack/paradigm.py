"""Verified, exact-match support for the Paradigm Kryptos PK1–PK10 corpus.

This module is intentionally *not* an all-purpose ``PK solver``.  It recognizes
one of ten recovered canonical ciphertexts after A--Z normalization and returns
the corresponding verified construction and plaintext.  A same-length or
similarly shaped ciphertext does not match and remains a normal cryptanalysis
problem.

Keeping this narrow boundary matters: a corpus match is deterministic evidence;
a language-model score or a story fitted to arbitrary text is not.  The catalog
is generated from ``kryptos/pk_submission_manifest.json`` by
``scripts/build_paradigm_catalog.py`` and ships with the Python package so the
desktop app works offline.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from importlib import resources
from typing import Any

from .lang import LanguageModel
from .results import Candidate
from .text import letters_only

CATALOG_RESOURCE = "paradigm_kryptos.json"


@dataclass(frozen=True)
class ParadigmRecord:
    """One exact, recovered PK corpus entry."""

    challenge_id: str
    title: str
    mechanism: str
    key: str
    ciphertext: str
    plaintext: str
    ciphertext_length: int
    plaintext_length: int
    plaintext_sha256: str
    verification: str

    @property
    def cipher_name(self) -> str:
        return f"paradigm_kryptos_{self.challenge_id.lower()}"

    @property
    def ciphertext_sha256(self) -> str:
        return hashlib.sha256(self.ciphertext.encode("ascii")).hexdigest()

    def as_dict(self, *, include_text: bool = False) -> dict[str, Any]:
        """A JSON-safe public description, optionally including corpus text."""
        result: dict[str, Any] = {
            "id": self.challenge_id,
            "title": self.title,
            "mechanism": self.mechanism,
            "key": self.key,
            "ciphertext_length": self.ciphertext_length,
            "plaintext_length": self.plaintext_length,
            "plaintext_sha256": self.plaintext_sha256,
            "ciphertext_sha256": self.ciphertext_sha256,
            "verification": self.verification,
        }
        if include_text:
            result.update({"ciphertext": self.ciphertext, "plaintext": self.plaintext})
        return result


def normalize(text: str) -> str:
    """The canonical PK comparison representation: uppercase A--Z only."""
    return letters_only(text).upper()


def _load_catalog() -> tuple[ParadigmRecord, ...]:
    raw = resources.files("buttcrack").joinpath("data", CATALOG_RESOURCE).read_text(encoding="utf-8")
    records = []
    for item in json.loads(raw):
        record = ParadigmRecord(
            challenge_id=str(item["id"]),
            title=str(item["title"]),
            mechanism=str(item["mechanism"]),
            key=str(item["key"]),
            ciphertext=str(item["ciphertext"]),
            plaintext=str(item["plaintext"]),
            ciphertext_length=int(item["ciphertext_length"]),
            plaintext_length=int(item["plaintext_length"]),
            plaintext_sha256=str(item["plaintext_sha256"]),
            verification=str(item["verification"]),
        )
        if len(record.ciphertext) != record.ciphertext_length or len(record.plaintext) != record.plaintext_length:
            raise ValueError(f"invalid Paradigm Kryptos catalog record {record.challenge_id}")
        if hashlib.sha256(record.plaintext.encode("ascii")).hexdigest() != record.plaintext_sha256:
            raise ValueError(f"invalid plaintext digest for {record.challenge_id}")
        records.append(record)
    return tuple(records)


RECORDS = _load_catalog()
BY_CIPHERTEXT = {record.ciphertext: record for record in RECORDS}


def catalog(*, include_text: bool = False) -> list[dict[str, Any]]:
    """Return PK1--PK10 in numeric order for an offline UI or API."""
    return [record.as_dict(include_text=include_text) for record in RECORDS]


def match(ciphertext: str) -> ParadigmRecord | None:
    """Return a record only when the normalized ciphertext is byte-for-byte known."""
    return BY_CIPHERTEXT.get(normalize(ciphertext))


def exact_candidate(ciphertext: str, model: LanguageModel) -> Candidate | None:
    """Build a **verified corpus-match** candidate, or ``None``.

    The confidence is exactly one because it comes from an exact ciphertext
    equality plus a stored SHA-256 of the recovered plaintext, not from the
    language model.  The model score remains attached for normal report fields
    and word respacing; it is not used as the proof.
    """
    record = match(ciphertext)
    if record is None:
        return None
    score = model.score(record.plaintext)
    return Candidate(
        plaintext=record.plaintext,
        cipher=record.cipher_name,
        key=record.key,
        confidence=1.0,
        fitness=score.fitness,
        score=score,
        notes={
            "method": "exact canonical-corpus match; recovered construction verified locally",
            "verification": record.verification,
            "verification_status": "verified exact match",
            "corpus_match": record.challenge_id,
            "title": record.title,
            "mechanism": record.mechanism,
            "plaintext_sha256": record.plaintext_sha256,
            "ciphertext_sha256": record.ciphertext_sha256,
            "caveat": (
                "This is an exact match to the recovered PK1–PK10 corpus, not a claim that "
                "arbitrary similar ciphertext has been automatically solved."
            ),
        },
    )
