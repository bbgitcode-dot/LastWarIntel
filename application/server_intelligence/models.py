"""
Sentinel
Server Intelligence Models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from analytics.intelligence.indicators import StrategicIndicator
from analytics.reasoning.models import IntelligenceFact


class ServerRecommendationPriority(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


@dataclass(slots=True, frozen=True)
class ServerRecommendation:
    """
    Structured strategic recommendation for one server.
    """

    title: str
    description: str
    priority: ServerRecommendationPriority


@dataclass(slots=True, frozen=True)
class ServerIntelligenceAssessment:
    """
    Strategic assessment for one server.
    """

    server: int

    status: str

    indicators: list[StrategicIndicator] = field(default_factory=list)

    recommendation: ServerRecommendation | None = None

    critical_facts: list[IntelligenceFact] = field(default_factory=list)
    high_facts: list[IntelligenceFact] = field(default_factory=list)
    facts: list[IntelligenceFact] = field(default_factory=list)