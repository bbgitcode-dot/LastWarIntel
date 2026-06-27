"""
Sentinel
Reasoning Models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from analytics.intelligence.indicators import StrategicIndicator


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


class HypothesisType(Enum):
    """
    Strategic hypothesis type.
    """

    COLLAPSE_RISK = "Collapse Risk"
    RECRUITMENT_WINDOW = "Recruitment Window"
    STRENGTH_INCREASE = "Strength Increase"
    STRUCTURAL_INSTABILITY = "Structural Instability"
    UNKNOWN = "Unknown"


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
class ReasoningContext:
    """
    Input for strategic reasoning.
    """

    facts: list[IntelligenceFact] = field(default_factory=list)

    indicators: list[StrategicIndicator] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class ReasoningHypothesis:
    """
    Strategic hypothesis derived from facts and indicators.
    """

    hypothesis_type: HypothesisType

    title: str

    description: str

    confidence: float

    severity: FactSeverity

    evidence: list[str] = field(default_factory=list)

    tags: list[str] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class Assessment:
    """
    Human-readable assessment generated
    from one or more intelligence facts or hypotheses.
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
    """

    facts: list[IntelligenceFact] = field(default_factory=list)

    indicators: list[StrategicIndicator] = field(default_factory=list)

    hypotheses: list[ReasoningHypothesis] = field(default_factory=list)

    assessment: Assessment | None = None

    recommendation: Recommendation | None = None