"""
Sentinel
Alliance Provider
"""

from __future__ import annotations

from analytics.alliance_intelligence.analyzer import (
    AllianceIntelligenceAnalyzer,
)
from analytics.comparison.models import DifferenceSet
from analytics.intelligence.provider import IntelligenceProvider
from analytics.reasoning.models import IntelligenceFact


class AllianceProvider(
    IntelligenceProvider,
):

    @property
    def entity_name(
        self,
    ) -> str:

        return "Alliance"

    def __init__(self) -> None:

        self._analyzer = (
            AllianceIntelligenceAnalyzer()
        )

    def analyze(
        self,
        differences: DifferenceSet,
    ) -> list[IntelligenceFact]:

        return self._analyzer.analyze(
            differences,
        ).facts