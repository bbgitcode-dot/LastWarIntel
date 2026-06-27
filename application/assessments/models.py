"""
Sentinel
Assessment Models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AssessmentSeverity(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


@dataclass(slots=True, frozen=True)
class Assessment:
    """
    Reusable strategic assessment.

    Assessments summarize a situation and can be reused
    by dashboard, reports, Discord, API and future UI renderers.
    """

    title: str

    summary: str

    severity: AssessmentSeverity

    confidence: float

    recommendation: str

    evidence: list[str] = field(default_factory=list)

    source: str = ""