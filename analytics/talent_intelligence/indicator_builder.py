"""
Sentinel
Talent Indicator Builder
"""

from __future__ import annotations

from analytics.intelligence.indicators import (
    IndicatorLevel,
    IndicatorScope,
    StrategicIndicator,
)
from analytics.talent_intelligence.models import TalentAssessment


class TalentIndicatorBuilder:
    """
    Converts talent assessments into strategic indicators.
    """

    def build(
        self,
        assessment: TalentAssessment,
    ) -> list[StrategicIndicator]:

        metrics = assessment.metrics

        return [
            StrategicIndicator(
                title="Talent Value",
                value=metrics.recruitment_value_score,
                scope=IndicatorScope.ALLIANCE,
                level=self._level_from_score(
                    metrics.recruitment_value_score,
                ),
                unit="",
                summary=self._talent_summary(
                    assessment,
                ),
                tags=[
                    "talent",
                    "recruitment",
                    "value",
                ],
            ),
            StrategicIndicator(
                title="Roster Structure",
                value=metrics.recruitment_efficiency,
                scope=IndicatorScope.ALLIANCE,
                level=self._level_from_score(
                    metrics.recruitment_efficiency,
                ),
                unit="%",
                summary=self._structure_summary(
                    assessment,
                ),
                tags=[
                    "talent",
                    "structure",
                    "roster",
                ],
            ),
            StrategicIndicator(
                title="Power Concentration",
                value=metrics.top5_concentration,
                scope=IndicatorScope.ALLIANCE,
                level=self._concentration_level(
                    metrics.top5_concentration,
                ),
                unit="%",
                summary=(
                    f"Top 5 players hold {metrics.top5_concentration}% "
                    "of total observed power."
                ),
                tags=[
                    "talent",
                    "structure",
                    "concentration",
                ],
            ),
            StrategicIndicator(
                title="Dependency Index",
                value=metrics.dependency_index,
                scope=IndicatorScope.ALLIANCE,
                level=self._concentration_level(
                    metrics.dependency_index,
                ),
                unit="",
                summary=(
                    "Estimated dependency on strongest players."
                ),
                tags=[
                    "talent",
                    "structure",
                    "dependency",
                ],
            ),
        ]

    @staticmethod
    def _talent_summary(
        assessment: TalentAssessment,
    ) -> str:

        metrics = assessment.metrics

        return (
            f"{metrics.players_180_plus} player(s) above 180M, "
            f"{metrics.players_200_plus} above 200M, "
            f"{metrics.players_250_plus} above 250M, "
            f"{metrics.players_300_plus} above 300M."
        )

    @staticmethod
    def _structure_summary(
        assessment: TalentAssessment,
    ) -> str:

        metrics = assessment.metrics

        return (
            f"{metrics.below_180_percent}% below 180M, "
            f"{metrics.recruitment_efficiency}% above 200M, "
            f"{metrics.whale_density}% above 300M."
        )

    @staticmethod
    def _level_from_score(
        score: float,
    ) -> IndicatorLevel:

        if score >= 80:
            return IndicatorLevel.CRITICAL

        if score >= 55:
            return IndicatorLevel.HIGH

        if score >= 30:
            return IndicatorLevel.MEDIUM

        return IndicatorLevel.LOW

    @staticmethod
    def _concentration_level(
        score: float,
    ) -> IndicatorLevel:

        if score >= 80:
            return IndicatorLevel.CRITICAL

        if score >= 60:
            return IndicatorLevel.HIGH

        if score >= 40:
            return IndicatorLevel.MEDIUM

        return IndicatorLevel.LOW