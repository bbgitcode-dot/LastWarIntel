"""
Sentinel
Entity Matching Models
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MatchDecision(Enum):
    MATCH = "Match"
    POSSIBLE_MATCH = "Possible Match"
    NO_MATCH = "No Match"


@dataclass(slots=True, frozen=True)
class MatchCandidate:
    """
    One entity that can be matched.
    """

    identifier: str

    name: str

    server: int | None = None

    alliance: str | None = None

    power: float | None = None


@dataclass(slots=True, frozen=True)
class MatchResult:
    """
    Result of comparing two match candidates.
    """

    baseline: MatchCandidate

    current: MatchCandidate

    confidence: float

    decision: MatchDecision

    reasons: list[str]