"""
Sentinel
Whale Intelligence Models
"""

from __future__ import annotations

from dataclasses import dataclass, field

from analytics.reasoning.models import IntelligenceFact


@dataclass(slots=True, frozen=True)
class WhaleEvent:
    """
    Represents one detected whale event.
    """

    identifier: str
    event: str
    power: float | None
    confidence: float
    payload: dict


@dataclass(slots=True, frozen=True)
class WhaleAssessment:
    """
    Result of whale analysis.
    """

    whales: list[WhaleEvent] = field(default_factory=list)

    facts: list[IntelligenceFact] = field(default_factory=list)

    incoming: int = 0
    outgoing: int = 0
    moved: int = 0