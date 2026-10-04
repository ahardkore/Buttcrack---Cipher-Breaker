"""Small sequential attack queue with JSON-safe checkpoints."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class QueueJob:
    name: str
    runner: Callable[[], Any]
    status: str = "queued"
    result: Any = None


@dataclass
class AttackQueue:
    jobs: list[QueueJob] = field(default_factory=list)

    def add(self, name: str, runner: Callable[[], Any]) -> None:
        self.jobs.append(QueueJob(name, runner))

    def run_next(self) -> QueueJob | None:
        job = next((item for item in self.jobs if item.status == "queued"), None)
        if job is None:
            return None
        job.status = "running"
        try:
            job.result = job.runner()
            job.status = "completed"
        except Exception as error:  # retain failure as data for the ledger
            job.result = {"error": str(error)}
            job.status = "failed"
        return job

    def checkpoint(self) -> list[dict[str, Any]]:
        return [{"name": j.name, "status": j.status, "result": j.result} for j in self.jobs]
