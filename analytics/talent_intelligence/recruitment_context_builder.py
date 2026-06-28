"""
Sentinel
Recruitment Context Builder
"""

from __future__ import annotations

from analytics.intelligence.indicators import StrategicIndicator
from analytics.talent_intelligence.recruitment_context import (
    RecruitmentContext,
)


class RecruitmentContextBuilder:
    """
    Builds a RecruitmentContext from strategic indicators.

    This builder translates existing Sentinel intelligence
    into the input model required by RecruitmentValueCalculator.
    """

    def build(
        self,
        indicators: list[StrategicIndicator],
    ) -> RecruitmentContext:

        return RecruitmentContext(
            talent_value=self._indicator(
                indicators,
                "Talent Value",
            ),
            structural_health=self._indicator(
                indicators,
                "Structural Health",
            ),
            recruitability=self._indicator(
                indicators,
                "Recruitability",
            ),
            whale_density=self._indicator(
                indicators,
                "Whale Density",
            ),
            elite_density=self._indicator(
                indicators,
                "Elite Density",
            ),
            recruitable_density=self._indicator(
                indicators,
                "Recruitable Density",
            ),
            momentum=self._indicator(
                indicators,
                "Recruitment Momentum",
            ),
        )

    @staticmethod
    def _indicator(
        indicators: list[StrategicIndicator],
        title: str,
    ) -> float:

        for indicator in indicators:
            if indicator.title == title:
                return float(indicator.value)

        return 0.0