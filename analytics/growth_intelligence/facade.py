"""
Sentinel
Growth Intelligence Facade
"""

from __future__ import annotations

from analytics.comparison.models import DifferenceSet
from analytics.growth_intelligence.analyzer import (
    GrowthIntelligenceAnalyzer,
)


class GrowthIntelligenceFacade:
    """
    Public entry point for growth intelligence.
    """

    def __init__(self) -> None:
        self._analyzer = GrowthIntelligenceAnalyzer()

    def analyze(
        self,
        differences: DifferenceSet,
    ):
        return self._analyzer.analyze(
            differences,
        )