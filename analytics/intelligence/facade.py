"""
LastWarIntel
Intelligence Facade
Version: 1.0

High-level API for strategic intelligence.
"""

from __future__ import annotations

from dataclasses import dataclass

from analytics.application.models import EntityReport
from analytics.intelligence.hypothesis_engine import HypothesisEngine
from analytics.intelligence.models import (
    Hypothesis,
    StrategicAssessment,
)


@dataclass(slots=True, frozen=True)
class IntelligenceResult:
    """
    Complete strategic intelligence.
    """

    assessment: StrategicAssessment


class IntelligenceFacade:
    """
    High-level API for strategic intelligence.
    """

    def __init__(self) -> None:
        self._hypotheses = HypothesisEngine()

    def analyze(
        self,
        report: EntityReport,
    ) -> IntelligenceResult:

        hypotheses: list[Hypothesis] = self._hypotheses.analyze(report)

        assessment = StrategicAssessment(
            server=report.server,
            alliance=report.alliance,
            hypotheses=hypotheses,
            recommendations=[],
        )

        return IntelligenceResult(
            assessment=assessment,
        )