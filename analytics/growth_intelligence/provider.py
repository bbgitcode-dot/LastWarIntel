"""
Sentinel
Growth Provider
"""

from __future__ import annotations

from analytics.comparison.models import DifferenceSet
from analytics.growth_intelligence.analyzer import (
    GrowthIntelligenceAnalyzer,
)
from analytics.intelligence.provider import IntelligenceProvider
from analytics.reasoning.models import IntelligenceFact


class GrowthProvider(
    IntelligenceProvider,
):
    """
    Intelligence provider for growth and decline signals.
    """

    @property
    def entity_name(
        self,
    ) -> str:
        return "Growth"

    def __init__(self) -> None:
        self._analyzer = GrowthIntelligenceAnalyzer()

    def analyze(
        self,
        differences: DifferenceSet,
    ) -> list[IntelligenceFact]:
        return self._analyzer.analyze(
            differences,
        ).facts