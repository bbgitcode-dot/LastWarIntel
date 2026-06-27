"""
Sentinel
Health Intelligence Facade
"""

from __future__ import annotations

from analytics.comparison.models import DifferenceSet
from analytics.health_intelligence.analyzer import (
    HealthIntelligenceAnalyzer,
)
from analytics.health_intelligence.indicator_builder import (
    HealthIndicatorBuilder,
)
from analytics.health_intelligence.models import HealthAssessment


class HealthIntelligenceFacade:
    """
    Public entry point for structural health intelligence.
    """

    def __init__(
        self,
    ) -> None:

        self._analyzer = HealthIntelligenceAnalyzer()
        self._indicator_builder = HealthIndicatorBuilder()

    def analyze(
        self,
        differences: DifferenceSet,
    ) -> HealthAssessment:

        assessment = self._analyzer.analyze(
            differences,
        )

        indicators = self._indicator_builder.build(
            assessment,
        )

        return HealthAssessment(
            score=assessment.score,
            signals=assessment.signals,
            indicators=indicators,
        )