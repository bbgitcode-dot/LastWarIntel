"""
Sentinel
Watchlist Facade
"""

from __future__ import annotations

from analytics.intelligence.indicators import StrategicIndicator
from analytics.opportunity_intelligence.models import (
    OpportunityAssessment,
)
from analytics.reasoning.models import IntelligenceFact

from application.assessments.models import Assessment
from application.watchlist.builder import (
    WatchlistBuilder,
)
from application.watchlist.repository import (
    WatchlistRepository,
)


class WatchlistFacade:
    """
    Public entry point for watchlist management.
    """

    def __init__(
        self,
        repository: WatchlistRepository | None = None,
    ) -> None:
        self._repository = repository or WatchlistRepository()
        self._builder = WatchlistBuilder()

    @property
    def repository(
        self,
    ) -> WatchlistRepository:
        return self._repository

    def add_from_opportunities(
        self,
        server: int,
        alliance: str | None,
        opportunities: list[OpportunityAssessment],
        indicators: list[StrategicIndicator],
        facts: list[IntelligenceFact],
        assessment: Assessment | None = None,
    ) -> int:
        targets = self._builder.build_from_opportunities(
            server=server,
            alliance=alliance,
            opportunities=opportunities,
            indicators=indicators,
            facts=facts,
            assessment=assessment,
        )

        before = self._repository.count()

        self._repository.extend(
            targets,
        )

        return self._repository.count() - before

    def top(
        self,
        limit: int = 10,
    ):
        return self._repository.top(
            limit,
        )