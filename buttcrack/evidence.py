"""Evidence labels for cryptanalytic results.

Scores rank candidates; they do not prove them.  This small dependency-free
module gives callers a common vocabulary and a strict promotion gate.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EvidenceStatus(str, Enum):
    OBSERVATION = "observation"
    HYPOTHESIS = "hypothesis"
    HEURISTIC = "heuristic_candidate"
    REPRODUCED = "reproduced"
    VERIFIED = "independently_verified"
    REJECTED = "rejected"


@dataclass(frozen=True)
class Evidence:
    status: EvidenceStatus
    score: float | None = None
    exact_round_trip: bool = False
    independent_recheck: bool = False
    note: str = ""

    def can_claim_solution(self) -> bool:
        """Only exact round-trip plus an independent recheck is a solution."""
        return (
            self.status is EvidenceStatus.VERIFIED
            and self.exact_round_trip
            and self.independent_recheck
        )

    def promote(self, *, exact_round_trip: bool, independent_recheck: bool) -> "Evidence":
        """Return a new status; never silently promote a score-only candidate."""
        if exact_round_trip and independent_recheck:
            status = EvidenceStatus.VERIFIED
        elif exact_round_trip:
            status = EvidenceStatus.REPRODUCED
        else:
            status = EvidenceStatus.HEURISTIC
        return Evidence(status, self.score, exact_round_trip, independent_recheck, self.note)
