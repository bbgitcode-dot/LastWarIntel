"""
Sentinel
Whale Provider
"""

from __future__ import annotations

from analytics.comparison.models import DifferenceSet
from analytics.intelligence.provider import IntelligenceProvider
from analytics.reasoning.models import IntelligenceFact
from analytics.whale.analyzer import WhaleAnalyzer


class WhaleProvider(
    IntelligenceProvider,
):

    @property
    def entity_name(
        self,
    ) -> str:

        return "Whale"

    def __init__(self) -> None:

        self._analyzer = WhaleAnalyzer()

    def analyze(
        self,
        differences: DifferenceSet,
    ) -> list[IntelligenceFact]:

        return self._analyzer.analyze(
            differences,
        ).facts