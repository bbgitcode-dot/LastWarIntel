"""
Sentinel
Whale Facade
"""

from __future__ import annotations

from analytics.comparison.models import DifferenceSet
from analytics.whale.analyzer import WhaleAnalyzer


class WhaleFacade:
    """
    Public entry point for whale intelligence.
    """

    def __init__(self) -> None:

        self._analyzer = WhaleAnalyzer()

    def analyze(
        self,
        differences: DifferenceSet,
    ):
        return self._analyzer.analyze(
            differences,
        )