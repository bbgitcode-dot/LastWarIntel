"""
Sentinel
Growth Intelligence Models
"""

from __future__ import annotations

from dataclasses import dataclass, field

from analytics.reasoning.models import IntelligenceFact


@dataclass(slots=True, frozen=True)
class GrowthEvent:
    """
    Represents one detected growth event.
    """

    identifier: str
    event: str
    change_percent: float
    confidence: float
    payload: dict


@dataclass(slots=True, frozen=True)
class GrowthAssessment:
    """
    Result of growth intelligence analysis.
    """

    events: list[GrowthEvent] = field(default_factory=list)
    facts: list[IntelligenceFact] = field(default_factory=list)

    growth: int = 0
    decline: int = 0