"""
Sentinel
Recruitment Advisor Models
"""

from __future__ import annotations

from dataclasses import dataclass, field

from analytics.opportunity_intelligence.models import (
    OpportunityAssessment,
)
from analytics.reasoning.models import IntelligenceFact


@dataclass(slots=True, frozen=True)
class RecruitmentTarget:
    """
    One ranked recruitment target.
    """

    name: str

    server: int

    alliance: str | None

    score: float

    priority: str

    summary: str

    evidence: list[str] = field(default_factory=list)

    facts: list[IntelligenceFact] = field(default_factory=list)

    opportunity: OpportunityAssessment | None = None


@dataclass(slots=True, frozen=True)
class RecruitmentAdvisorResult:
    """
    Recruitment advisor output.
    """

    server: int

    targets: list[RecruitmentTarget] = field(default_factory=list)

    recommendation: str = ""