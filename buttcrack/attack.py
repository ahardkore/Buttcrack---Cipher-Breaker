"""Common attack-job protocol for explainable and resumable searches."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class AttackResult:
    attack: str
    status: str = "running"
    progress: float = 0.0
    best_score: float | None = None
    candidates: list[dict[str, Any]] = field(default_factory=list)
    checkpoint: dict[str, Any] = field(default_factory=dict)
    message: str = ""


class AttackJob(Protocol):
    name: str

    def run(self) -> AttackResult:
        """Run or resume a bounded attack."""

    def save_checkpoint(self) -> dict[str, Any]:
        """Return JSON-serializable state."""

    def verify(self, candidate: dict[str, Any]) -> Any:
        """Perform exact verification; never infer it from score."""


def merge_result(previous: AttackResult, current: AttackResult) -> AttackResult:
    """Merge resumable progress while retaining the strongest candidates."""
    candidates = previous.candidates + current.candidates
    candidates.sort(key=lambda item: item.get("score", float("-inf")), reverse=True)
    unique = []
    seen = set()
    for candidate in candidates:
        key = repr(sorted(candidate.items()))
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return AttackResult(
        attack=current.attack or previous.attack,
        status=current.status,
        progress=max(previous.progress, current.progress),
        best_score=max(x for x in (previous.best_score, current.best_score) if x is not None)
        if any(x is not None for x in (previous.best_score, current.best_score))
        else None,
        candidates=unique[:100],
        checkpoint=current.checkpoint or previous.checkpoint,
        message=current.message,
    )
