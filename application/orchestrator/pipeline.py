"""
Sentinel
Operations Pipeline
"""

from __future__ import annotations

from analytics.intelligence.indicators import StrategicIndicator
from analytics.opportunity_intelligence.facade import (
    OpportunityIntelligenceFacade,
)
from analytics.opportunity_intelligence.models import (
    OpportunityContext,
)
from analytics.reasoning.models import IntelligenceFact

from application.briefing.facade import MorningBriefingFacade
from application.orchestrator.models import (
    SentinelResult,
)
from application.reports.facade import (
    ReportsFacade,
)
from application.watchlist.facade import (
    WatchlistFacade,
)


class OperationsPipeline:
    """
    Connects Intelligence with Operations.
    """

    def __init__(
        self,
    ) -> None:

        self._opportunity = OpportunityIntelligenceFacade()

        self._watchlist = WatchlistFacade()

        self._reports = ReportsFacade()

        self._briefing = MorningBriefingFacade()

    def execute(
        self,
        server: int,
        alliance: str,
        facts: list[IntelligenceFact],
        indicators: list[StrategicIndicator],
    ) -> SentinelResult:

        context = OpportunityContext(
            server=server,
            alliance=alliance,
            facts=facts,
            indicators=indicators,
        )

        opportunities = self._opportunity.analyze(
            context,
        )

        self._watchlist.add_from_opportunities(
            server=server,
            alliance=alliance,
            opportunities=opportunities,
            indicators=indicators,
            facts=facts,
        )

        watch_targets = self._watchlist.top()

        report = self._reports.morning_report(
            watch_targets,
        )

        briefing = self._briefing.create(
			server=server,
			watch_targets=watch_targets,
			breaking_news=[],
		)

        return SentinelResult(
            briefing=briefing,
            opportunities=opportunities,
            watch_targets=watch_targets,
            report=report,
        )