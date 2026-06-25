"""
LastWarIntel
Timeline Facade
Version: 1.0

High-level entry point for temporal intelligence.

Orchestrates timeline creation, metrics computation and trend detection.
"""

from __future__ import annotations

from dataclasses import dataclass

from analytics.timeline.analyzer import TimelineAnalyzer
from analytics.timeline.metrics import (
    TimelineMetrics,
    TimelineMetricsBuilder,
)
from analytics.timeline.models import (
    AllianceTimeline,
    TimelineAssessment,
)
from analytics.timeline.trend_detector import TrendDetector


@dataclass(slots=True)
class TimelineResult:
    """
    Complete temporal intelligence for one alliance.
    """

    timeline: AllianceTimeline
    metrics: TimelineMetrics
    assessment: TimelineAssessment


class TimelineFacade:
    """
    High-level API for temporal intelligence.

    Consumers should use this class instead of directly invoking
    TimelineAnalyzer, TimelineMetricsBuilder and TrendDetector.
    """

    def __init__(self) -> None:
        self._analyzer = TimelineAnalyzer()
        self._metrics = TimelineMetricsBuilder()
        self._trend = TrendDetector()

    def analyze(
        self,
        server: int,
        alliance: str,
    ) -> TimelineResult | None:

        timeline = self._analyzer.analyze_alliance(
            server,
            alliance,
        )

        if timeline is None:
            return None

        metrics = self._metrics.build(timeline)
        assessment = self._trend.detect(metrics)

        return TimelineResult(
            timeline=timeline,
            metrics=metrics,
            assessment=assessment,
        )