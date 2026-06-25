"""
LastWarIntel
Timeline Trend Detector
Version: 1.0

Detects long-term alliance trends from objective timeline metrics.
"""

from __future__ import annotations

from analytics.timeline.metrics import TimelineMetrics
from analytics.timeline.models import (
    TimelineAssessment,
    TrendType,
)


class TrendDetector:
    """
    Converts timeline metrics into high-level trend assessments.
    """

    def detect(
        self,
        metrics: TimelineMetrics,
    ) -> TimelineAssessment:

        trend = TrendType.UNKNOWN
        confidence = 70.0
        summary = "No clear long-term trend detected."
        evidence: list[str] = []

        #
        # Missing latest snapshot
        #
        if metrics.missing_latest_snapshot:
            trend = TrendType.COLLAPSING
            confidence = 95.0
            summary = (
                "Alliance disappeared from the latest snapshot."
            )

            evidence.append(
                "Missing from latest available snapshot."
            )

        #
        # Recovery
        #
        elif (
            metrics.max_drop_percent <= -10
            and metrics.total_growth_percent > 0
        ):

            trend = TrendType.RECOVERING
            confidence = 92.0
            summary = (
                "Alliance recovered after an earlier decline."
            )

            evidence.append(
                f"Maximum decline: {metrics.max_drop_percent:.2f}%"
            )
            evidence.append(
                f"Overall growth: {metrics.total_growth_percent:.2f}%"
            )

        #
        # Strong Growth
        #
        elif (
            metrics.total_growth_percent >= 15
            and metrics.power_volatility < 15
        ):

            trend = TrendType.GROWING
            confidence = 90.0
            summary = (
                "Alliance shows sustained long-term growth."
            )

            evidence.append(
                f"Growth: {metrics.total_growth_percent:.2f}%"
            )

        #
        # Declining
        #
        elif metrics.total_growth_percent <= -10:

            trend = TrendType.DECLINING
            confidence = 88.0
            summary = (
                "Alliance is steadily losing power."
            )

            evidence.append(
                f"Growth: {metrics.total_growth_percent:.2f}%"
            )

        #
        # Stable
        #
        elif abs(metrics.total_growth_percent) < 5:

            trend = TrendType.STABLE
            confidence = 85.0
            summary = (
                "Alliance remains relatively stable."
            )

        #
        # Volatile
        #
        elif metrics.power_volatility > 20:

            trend = TrendType.VOLATILE
            confidence = 83.0
            summary = (
                "Alliance shows high internal volatility."
            )

            evidence.append(
                f"Volatility: {metrics.power_volatility:.2f}%"
            )

        return TimelineAssessment(
            server=metrics.server,
            alliance=metrics.alliance,
            trend=trend,
            confidence=confidence,
            summary=summary,
            evidence=evidence,
        )