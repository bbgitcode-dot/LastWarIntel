"""
Sentinel
Comparison Facade
"""

from __future__ import annotations

from analytics.comparison.analyzer import ComparisonAnalyzer
from analytics.comparison.detector import DifferenceDetector
from analytics.comparison.difference import EntityType
from analytics.domain.comparison import Comparison
from analytics.matching.models import MatchCandidate


class ComparisonFacade:
    """
    Public entry point for snapshot comparisons.
    """

    def __init__(self) -> None:
        self._analyzer = ComparisonAnalyzer()
        self._detector = DifferenceDetector()

    def analyze(
        self,
        comparison: Comparison,
    ):
        return self._analyzer.analyze(
            comparison,
        )

    def detect_differences(
        self,
        comparison: Comparison,
    ):
        return self._analyzer.detect_differences(
            comparison,
        )

    def detect_candidate_differences(
        self,
        entity_type: EntityType,
        baseline: list[MatchCandidate],
        current: list[MatchCandidate],
    ):
        return self._detector.detect(
            entity_type=entity_type,
            baseline=baseline,
            current=current,
        )