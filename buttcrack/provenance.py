"""Auditable provenance records for assistant/model suggestions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class AssistantRecord:
    provider: str
    model: str
    prompt: str
    output: str
    ciphertext_sha256: str
    timestamp_utc: str
    affected_attack: bool = False
    evidence_status: str = "hypothesis"

    @classmethod
    def create(
        cls, provider: str, model: str, prompt: str, output: str, ciphertext: str, **kwargs
    ) -> AssistantRecord:
        return cls(
            provider,
            model,
            prompt,
            output,
            hashlib.sha256(ciphertext.encode()).hexdigest(),
            datetime.now(timezone.utc).isoformat(),
            **kwargs,
        )

    def save_jsonl(self, path: str | Path) -> None:
        with Path(path).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(self), ensure_ascii=False) + "\n")
