"""Portable, structured session files for reproducible cryptanalysis work."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class Project:
    ciphertext: str = ""
    source: str = ""
    normalization: str = "letters-only"
    assumptions: list[str] = field(default_factory=list)
    attacks: list[dict[str, Any]] = field(default_factory=list)
    candidates: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    verification: dict[str, Any] = field(default_factory=dict)
    crib_placements: list[dict[str, Any]] = field(default_factory=list)
    transposition: dict[str, Any] = field(default_factory=dict)
    scoring_records: list[dict[str, Any]] = field(default_factory=list)
    campaign: dict[str, Any] = field(default_factory=dict)
    assistant_outputs: list[dict[str, Any]] = field(default_factory=list)
    created_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    schema: str = "buttcrack-project/v2"

    @property
    def ciphertext_sha256(self):
        return hashlib.sha256(self.ciphertext.encode()).hexdigest()

    def add_attack(self, name, parameters, status="running"):
        self.attacks.append({"name": name, "parameters": parameters, "status": status})

    def add_candidate(self, plaintext, evidence):
        record = {"plaintext": plaintext, "evidence": dict(evidence), "verification_history": []}
        self.candidates.append(record)
        return record

    def record_candidate_verification(self, index, state, details=None):
        c = self.candidates[index]
        c.setdefault("verification_history", []).append(
            {"state": state, "details": details or {}, "utc": datetime.now(timezone.utc).isoformat()}
        )
        c["evidence"]["verification_state"] = state

    def save(self, path):
        payload = asdict(self)
        payload["ciphertext_sha256"] = self.ciphertext_sha256
        Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path):
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        payload.pop("ciphertext_sha256", None)
        payload.pop("schema", None)
        allowed = {f.name for f in fields(cls)}
        payload = {k: v for k, v in payload.items() if k in allowed}
        return cls(**payload)
