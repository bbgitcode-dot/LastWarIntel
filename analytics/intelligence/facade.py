"""
LastWarIntel
Intelligence Facade
Version: 1.2

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
from analytics.intelligence.outlook_engine import OutlookEngine
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
        self._outlook_engine = OutlookEngine()

    def analyze(
        self,
        report: EntityReport,
    ) -> IntelligenceResult:

        #
        # Generate hypotheses
        #

        hypotheses: list[Hypothesis] = self._hypothesis_engine.analyze(
            report
        )

        #
        # Initial assessment
        #

        assessment = StrategicAssessment(
            server=report.server,
            alliance=report.alliance,
            hypotheses=hypotheses,
        )

        #
        # Recommendations
        #

        assessment = self._recommendation_engine.generate(
            assessment
        )

        #
        # Risks, opportunities and outlook
        #

        assessment = self._outlook_engine.analyze(
            assessment
        )

        return IntelligenceResult(
            assessment=assessment,
        )