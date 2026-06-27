"""
Sentinel
Alliance Intelligence Facade
"""

from __future__ import annotations

from analytics.alliance_intelligence.analyzer import (
    AllianceIntelligenceAnalyzer,
)
from analytics.comparison.models import DifferenceSet


class AllianceIntelligenceFacade:
    """
    Public entry point for alliance intelligence.
    """

    def __init__(self) -> None:
        self._analyzer = AllianceIntelligenceAnalyzer()

    def analyze(
        self,
        differences: DifferenceSet,
    ):
        return self._analyzer.analyze(
            differences,
        )