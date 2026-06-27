"""
Sentinel
Comparison Analyzer
"""

from __future__ import annotations

from analytics.comparison.models import (
    ComparisonStatistics,
    DifferenceSet,
)
from analytics.domain.comparison import Comparison


class ComparisonAnalyzer:
    """
    Produces generic comparison statistics.

    This analyzer intentionally performs no
    business-specific interpretation.
    """

    def analyze(
        self,
        comparison: Comparison,
    ) -> ComparisonStatistics:

        duration = (
            comparison.duration.total_seconds()
            / 3600
        )

        return ComparisonStatistics(
            duration_hours=duration,
            alliance_changes=0,
            player_changes=0,
            power_delta=0.0,
        )

    def detect_differences(
        self,
        comparison: Comparison,
    ) -> DifferenceSet:
        """
        Detect generic differences between two snapshots.

        The current implementation is intentionally
        a placeholder.

        Once repositories are available, this method
        will populate the DifferenceSet.
        """

        return DifferenceSet()