"""
Sentinel
Recruitability Indicator Builder
"""

from __future__ import annotations

from analytics.intelligence.indicators import (
    IndicatorLevel,
    IndicatorScope,
    StrategicIndicator,
)
from analytics.recruitability_intelligence.models import (
    RecruitabilityAssessment,
)


class RecruitabilityIndicatorBuilder:
    """
    Converts recruitability assessments into strategic indicators.
    """

    def build(
        self,
        assessment: RecruitabilityAssessment,
    ) -> list[StrategicIndicator]:

        return [
            StrategicIndicator(
                title="Recruitability",
                value=assessment.score,
                scope=IndicatorScope.ALLIANCE,
                level=self._level_from_score(
                    assessment.score,
                ),
                unit="",
                summary=self._summary(
                    assessment,
                ),
                tags=[
                    "recruitability",
                    "recruitment",
                    "instability",
                ],
            )
        ]

    @staticmethod
    def _summary(
        assessment: RecruitabilityAssessment,
    ) -> str:

        if not assessment.signals:
            return "No significant recruitability signals detected."

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

        if score >= 80:
            return IndicatorLevel.CRITICAL

        if score >= 55:
            return IndicatorLevel.HIGH

        if score >= 30:
            return IndicatorLevel.MEDIUM

        return IndicatorLevel.LOW