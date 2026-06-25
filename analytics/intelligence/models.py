"""
LastWarIntel
Strategic Intelligence Models
Version: 1.0

Domain models for strategic reasoning.

These models represent conclusions derived from analytics,
not raw observations.
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
    Action recommended to the president.
    """

    title: str

    description: str

    priority: IntelligencePriority

    confidence: float

    rationale: list[str] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class StrategicAssessment:
    """
    Complete strategic assessment for one alliance.
    """

    server: int

    alliance: str

    hypotheses: list[Hypothesis] = field(default_factory=list)

    recommendations: list[Recommendation] = field(default_factory=list)