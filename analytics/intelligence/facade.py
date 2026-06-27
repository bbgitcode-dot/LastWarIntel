"""
LastWarIntel
Intelligence Facade
Version: 1.3

High-level API for strategic intelligence.
"""

from __future__ import annotations

from dataclasses import dataclass

from analytics.application.models import EntityReport
from analytics.intelligence.fact_adapter import IntelligenceFactAdapter
from analytics.intelligence.hypothesis_engine import HypothesisEngine
from analytics.intelligence.models import (
    Hypothesis,
    StrategicAssessment,
)
from analytics.intelligence.outlook_engine import OutlookEngine
from analytics.intelligence.recommendation_engine import RecommendationEngine
from analytics.reasoning.models import IntelligenceFact


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
        self._fact_adapter = IntelligenceFactAdapter()

    def analyze(
        self,
        report: EntityReport,
    ) -> IntelligenceResult:
        """
        Analyze an EntityReport using the legacy report-based pipeline.
        """

        hypotheses: list[Hypothesis] = self._hypothesis_engine.analyze(
            report
        )

        return self._build_result(
            server=report.server,
            alliance=report.alliance,
            hypotheses=hypotheses,
        )

    def analyze_facts(
        self,
        server: int,
        alliance: str,
        facts: list[IntelligenceFact],
    ) -> IntelligenceResult:
        """
        Analyze IntelligenceFact objects using the existing
        strategic assessment pipeline.
        """

        hypotheses = self._fact_adapter.convert(
            facts
        )

        return self._build_result(
            server=server,
            alliance=alliance,
            hypotheses=hypotheses,
        )

    def _build_result(
        self,
        server: int,
        alliance: str,
        hypotheses: list[Hypothesis],
    ) -> IntelligenceResult:
        assessment = StrategicAssessment(
            server=server,
            alliance=alliance,
            hypotheses=hypotheses,
        )

        assessment = self._recommendation_engine.generate(
            assessment
        )

        assessment = self._outlook_engine.analyze(
            assessment
        )

        return IntelligenceResult(
            assessment=assessment,
        )