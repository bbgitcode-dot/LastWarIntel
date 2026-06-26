"""
LastWarIntel
Ranking Facade
Version: 1.0

High-level API for strategic rankings.
"""

from __future__ import annotations

from dataclasses import dataclass

from analytics.ranking.analyzer import RankingAnalyzer
from analytics.ranking.models import Ranking


@dataclass(slots=True, frozen=True)
class RankingResult:
    """
    Container for all server rankings.
    """

    recruitment: Ranking
    growth: Ranking


class RankingFacade:
    """
    High-level API for ranking generation.
    """

    def __init__(self) -> None:
        self._analyzer = RankingAnalyzer()

    def analyze(
        self,
        server: int,
    ) -> RankingResult:

        return RankingResult(
            recruitment=self._analyzer.recruitment(server),
            growth=self._analyzer.growth(server),
        )

    def recruitment(
        self,
        server: int,
    ) -> Ranking:

        return self._analyzer.recruitment(server)

    def growth(
        self,
        server: int,
    ) -> Ranking:

        return self._analyzer.growth(server)