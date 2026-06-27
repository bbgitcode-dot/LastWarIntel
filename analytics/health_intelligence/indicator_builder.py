"""
Sentinel
Health Indicator Builder
"""

from __future__ import annotations

from analytics.health_intelligence.models import HealthAssessment
from analytics.intelligence.indicators import (
    IndicatorLevel,
    IndicatorScope,
    StrategicIndicator,
)


class HealthIndicatorBuilder:
    """
    Converts health assessments into strategic indicators.
    """

    def build(
        self,
        assessment: HealthAssessment,
    ) -> list[StrategicIndicator]:

        return [
            StrategicIndicator(
                title="Structural Health",
                value=assessment.score,
                scope=IndicatorScope.ALLIANCE,
                level=self._level_from_score(
                    assessment.score,
                ),
                unit="%",
                summary=self._summary(
                    assessment,
                ),
                tags=[
                    "health",
                    "stability",
                    "structure",
                ],
            )
        ]

    @staticmethod
    def _summary(
        assessment: HealthAssessment,
    ) -> str:

        if not assessment.signals:
            return "No structural instability signals detected."

        reasons = [
            signal.reason
            for signal in assessment.signals
        ]

        return " ".join(
            reasons
        )

    @staticmethod
    def _level_from_score(
        score: int,
    ) -> IndicatorLevel:

        if score <= 30:
            return IndicatorLevel.CRITICAL

        if score <= 55:
            return IndicatorLevel.HIGH

        if score <= 75:
            return IndicatorLevel.MEDIUM

        return IndicatorLevel.LOW