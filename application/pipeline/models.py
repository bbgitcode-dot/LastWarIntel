"""
Sentinel
Pipeline Models
"""

from __future__ import annotations

from dataclasses import dataclass, field

from analytics.intelligence.models import StrategicAssessment
from analytics.intelligence.repository import IntelligenceRepository
from analytics.reasoning.models import IntelligenceFact


@dataclass(slots=True, frozen=True)
class PipelineResult:
    """
    Result of a complete Sentinel pipeline run.
    """

    assessment: StrategicAssessment

    repository: IntelligenceRepository

    facts: list[IntelligenceFact] = field(default_factory=list)

    published_facts: int = 0