"""
Sentinel
Opportunity Intelligence Models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from analytics.intelligence.indicators import StrategicIndicator
from analytics.reasoning.models import IntelligenceFact


class OpportunityType(Enum):
    RECRUITMENT = "Recruitment"
    TRANSFER = "Transfer"
    DIPLOMACY = "Diplomacy"
    MERGER = "Merger"
    ATTACK = "Attack"
    UNKNOWN = "Unknown"


class OpportunityPriority(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


@dataclass(slots=True, frozen=True)
class OpportunityContext:
    """
    Context used to evaluate opportunities.

    Opportunity Intelligence works on already known
    facts and indicators, not directly on snapshots.
    """

    server: int

    alliance: str | None = None

    facts: list[IntelligenceFact] = field(default_factory=list)

    indicators: list[StrategicIndicator] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class OpportunityAssessment:
    """
    One detected strategic opportunity.
    """

    title: str

    description: str

    opportunity_type: OpportunityType

    priority: OpportunityPriority

    score: float

    confidence: float

    evidence: list[str] = field(default_factory=list)

    tags: list[str] = field(default_factory=list)