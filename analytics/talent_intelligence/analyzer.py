"""
Sentinel
Talent Intelligence Analyzer
"""

from __future__ import annotations

from statistics import median

from config.recruitment import (
    HIGH_VALUE_POWER,
    MIN_RECRUIT_POWER,
    TARGET_RECRUIT_POWER,
    WHALE_POWER,
)
from analytics.matching.models import MatchCandidate
from analytics.talent_intelligence.models import (
    TalentAssessment,
    TalentMetrics,
)


class TalentIntelligenceAnalyzer:
    """
    Calculates raw talent statistics.
    """

    def analyze(
        self,
        players: list[MatchCandidate],
    ) -> TalentAssessment:

        powers = sorted(
            [
                player.power
                for player in players
                if player.power is not None
            ],
            reverse=True,
        )

        if not powers:
            return TalentAssessment(
                metrics=TalentMetrics(
                    total_players=0,
                    players_below_180=0,
                    players_180_plus=0,
                    players_200_plus=0,
                    players_250_plus=0,
                    players_300_plus=0,
                    below_180_percent=0,
                    recruitment_efficiency=0,
                    whale_density=0,
                    elite_ratio=0,
                    average_power=0,
                    median_power=0,
                    total_power=0,
                    top5_power=0,
                    top10_power=0,
                    top5_concentration=0,
                    top10_concentration=0,
                    dependency_index=0,
                    recruitment_value_score=0,
                )
            )

        total_players = len(powers)
        total_power = sum(powers)

        players_below_180 = sum(
            power < MIN_RECRUIT_POWER
            for power in powers
        )

        players_180_plus = sum(
            power >= MIN_RECRUIT_POWER
            for power in powers
        )

        players_200_plus = sum(
            power >= TARGET_RECRUIT_POWER
            for power in powers
        )

        players_250_plus = sum(
            power >= HIGH_VALUE_POWER
            for power in powers
        )

        players_300_plus = sum(
            power >= WHALE_POWER
            for power in powers
        )

        top5_power = sum(
            powers[:5]
        )

        top10_power = sum(
            powers[:10]
        )

        return TalentAssessment(
            metrics=TalentMetrics(
                total_players=total_players,
                players_below_180=players_below_180,
                players_180_plus=players_180_plus,
                players_200_plus=players_200_plus,
                players_250_plus=players_250_plus,
                players_300_plus=players_300_plus,
                below_180_percent=self._percent(
                    players_below_180,
                    total_players,
                ),
                recruitment_efficiency=self._percent(
                    players_200_plus,
                    total_players,
                ),
                whale_density=self._percent(
                    players_300_plus,
                    total_players,
                ),
                elite_ratio=self._percent(
                    players_300_plus,
                    players_180_plus,
                ),
                average_power=round(
                    total_power / total_players,
                    2,
                ),
                median_power=median(powers),
                total_power=total_power,
                top5_power=top5_power,
                top10_power=top10_power,
                top5_concentration=self._percent(
                    top5_power,
                    total_power,
                ),
                top10_concentration=self._percent(
                    top10_power,
                    total_power,
                ),
                dependency_index=self._dependency_index(
                    powers,
                    total_power,
                ),
                recruitment_value_score=self._score(
                    players_180_plus,
                    players_200_plus,
                    players_250_plus,
                    players_300_plus,
                ),
            )
        )

    @staticmethod
    def _score(
        players_180_plus: int,
        players_200_plus: int,
        players_250_plus: int,
        players_300_plus: int,
    ) -> float:

        score = (
            players_180_plus * 1
            + players_200_plus * 2
            + players_250_plus * 4
            + players_300_plus * 8
        )

        return min(
            score,
            100,
        )

    @staticmethod
    def _percent(
        value: float,
        total: float,
    ) -> float:

        if total <= 0:
            return 0.0

        return round(
            value / total * 100,
            2,
        )

    @staticmethod
    def _dependency_index(
        powers: list[float],
        total_power: float,
    ) -> float:

        if not powers or total_power <= 0:
            return 0.0

        strongest_player_share = powers[0] / total_power * 100

        top3_share = sum(
            powers[:3]
        ) / total_power * 100

        return round(
            strongest_player_share * 0.6
            + top3_share * 0.4,
            2,
        )