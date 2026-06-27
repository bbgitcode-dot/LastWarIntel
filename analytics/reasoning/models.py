"""
Sentinel
Reasoning Models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


class FactSeverity(Enum):
    """
    Importance of an intelligence fact.
    """

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class FactEntityType(Enum):
    """
    Entity type a fact belongs to.
    """

    UNKNOWN = "Unknown"
    SERVER = "Server"
    ALLIANCE = "Alliance"
    PLAYER = "Player"
    CAMPAIGN = "Campaign"
    SNAPSHOT = "Snapshot"
    SYSTEM = "System"


@dataclass(slots=True, frozen=True)
class IntelligenceFact:
    """
    One atomic intelligence fact produced by an intelligence module.

    Facts are the common language between analytics,
    intelligence, reasoning, feeds, reports and entity pages.
    """

    source: str
    title: str
    description: str
    severity: FactSeverity

    confidence: float = 100.0

    evidence: list[str] = field(default_factory=list)

    entity_type: FactEntityType = FactEntityType.UNKNOWN
    entity_id: str = ""

    tags: list[str] = field(default_factory=list)

    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True, frozen=True)
class Assessment:
    """
    Human-readable assessment generated
    from one or more intelligence facts.
    """

    title: str
    summary: str


@dataclass(slots=True, frozen=True)
class Recommendation:
    """
    Suggested action.
    """

    title: str
    description: str
    priority: FactSeverity


@dataclass(slots=True, frozen=True)
class ReasoningResult:
    """
    Final reasoning output.

    Every reasoning result consists of

    Facts

    ↓

    Assessment

    ↓

    Recommendation
    """

    facts: list[IntelligenceFact] = field(default_factory=list)
    assessment: Assessment | None = None
    recommendation: Recommendation | None = None