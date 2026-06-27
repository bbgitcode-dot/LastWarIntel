"""
Sentinel
Alliance Intelligence Models
"""

from __future__ import annotations

from dataclasses import dataclass, field

from analytics.reasoning.models import IntelligenceFact


@dataclass(slots=True, frozen=True)
class AllianceEvent:
    """
    Represents one detected alliance event.
    """

    identifier: str
    event: str
    confidence: float
    payload: dict


@dataclass(slots=True, frozen=True)
class AllianceAssessment:
    """
    Result of alliance intelligence analysis.
    """

    events: list[AllianceEvent] = field(default_factory=list)
    facts: list[IntelligenceFact] = field(default_factory=list)

    added: int = 0
    removed: int = 0
    moved: int = 0
    modified: int = 0