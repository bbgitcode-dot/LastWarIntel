"""
LastWarIntel
Intelligence Facade
Version: 1.1

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
from analytics.intelligence.recommendation_engine import RecommendationEngine


@dataclass(slots=True, frozen=True)
class IntelligenceResult:
    """
    Complete strategic intelligence result.
    """

    assessment: StrategicAssessment


class IntelligenceFacade:
    """
    High-level API for strategic intelligence.
    """

    def __init__(self) -> None:
        self._hypothesis_engine = HypothesisEngine()
        self._recommendation_engine = RecommendationEngine()

    def analyze(
        self,
        report: EntityReport,
    ) -> IntelligenceResult:

        hypotheses: list[Hypothesis] = self._hypothesis_engine.analyze(
            report
        )

        assessment = StrategicAssessment(
            server=report.server,
            alliance=report.alliance,
            hypotheses=hypotheses,
            recommendations=[],
        )

        assessment = self._recommendation_engine.generate(
            assessment
        )

        return IntelligenceResult(
            assessment=assessment,
        )