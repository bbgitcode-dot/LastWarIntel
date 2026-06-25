"""
LastWarIntel
Timeline Models
Version: 1.0

Domain models for temporal intelligence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TrendType(Enum):
    GROWING = "Growing"
    DECLINING = "Declining"
    RECOVERING = "Recovering"
    COLLAPSING = "Collapsing"
    STABLE = "Stable"
    VOLATILE = "Volatile"
    UNKNOWN = "Unknown"


@dataclass(slots=True)
class TimelinePoint:
    collection: str
    rank: int
    power: int


@dataclass(slots=True)
class AllianceTimeline:
    server: int
    alliance: str
    points: list[TimelinePoint] = field(default_factory=list)

    @property
    def first(self) -> TimelinePoint | None:
        return self.points[0] if self.points else None

    @property
    def last(self) -> TimelinePoint | None:
        return self.points[-1] if self.points else None

    @property
    def count(self) -> int:
        return len(self.points)


@dataclass(slots=True)
class TimelineAssessment:
    server: int
    alliance: str
    trend: TrendType
    confidence: float
    summary: str
    evidence: list[str] = field(default_factory=list)