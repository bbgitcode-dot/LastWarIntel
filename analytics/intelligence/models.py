"""
LastWarIntel
Strategic Intelligence Models
Version: 2.0

Domain models for strategic reasoning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class IntelligencePriority(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class HypothesisCategory(Enum):
    COLLAPSE = "Collapse"
    RECOVERY = "Recovery"
    MERGER = "Merger"
    RECRUITMENT = "Recruitment"
    GROWTH = "Growth"
    DIPLOMACY = "Diplomacy"
    LEADERSHIP = "Leadership"
    UNKNOWN = "Unknown"


@dataclass(slots=True, frozen=True)
class Hypothesis:
    """
    Strategic conclusion derived from multiple signals.
    """

    title: str
    summary: str

    confidence: float

    priority: IntelligencePriority

    category: HypothesisCategory

    evidence: list[str] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class Recommendation:
    """
    Recommended strategic action.
    """

    title: str

    description: str

    priority: IntelligencePriority

    confidence: float

    rationale: list[str] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class StrategicRisk:
    """
    High-level strategic risk.
    """

    title: str
    summary: str
    confidence: float
    priority: IntelligencePriority


@dataclass(slots=True, frozen=True)
class StrategicOpportunity:
    """
    High-level opportunity.
    """

    title: str
    summary: str
    confidence: float
    priority: IntelligencePriority


@dataclass(slots=True, frozen=True)
class StrategicOutlook:
    """
    Overall outlook.
    """

    summary: str
    confidence: float


@dataclass(slots=True, frozen=True)
class StrategicAssessment:
    """
    Complete strategic assessment for one alliance.
    """

    server: int

    alliance: str

    hypotheses: list[Hypothesis] = field(default_factory=list)

    recommendations: list[Recommendation] = field(default_factory=list)

    risks: list[StrategicRisk] = field(default_factory=list)

    opportunities: list[StrategicOpportunity] = field(default_factory=list)

    outlook: StrategicOutlook | None = None