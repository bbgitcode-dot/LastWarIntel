"""
Sentinel
Server Landscape Builder
"""

from __future__ import annotations

from application.server_landscape.context import ServerLandscapeContext
from application.server_landscape.models import (
    ServerCard,
    ServerLandscape,
    ServerState,
)
from analytics.ranking.facade import RankingFacade
from analytics.server_intelligence.facade import ServerIntelligenceFacade
from analytics.validation.models import ValidationStatus
from analytics.validation.server_validator import (
    ServerValidationInput,
    ServerValidator,
)


class ServerLandscapeBuilder:
    """
    Builds the Server Landscape view model.
    """

    def __init__(self) -> None:
        self._ranking = RankingFacade()
        self._intelligence = ServerIntelligenceFacade()
        self._validator = ServerValidator()

    def build(
        self,
        context: ServerLandscapeContext,
    ) -> ServerLandscape:
        cards = [
            self._build_server_card(server)
            for server in context.monitored_servers
        ]

        return ServerLandscape(
            cards=cards,
            ready=sum(c.state == ServerState.READY for c in cards),
            partial=sum(c.state == ServerState.PARTIAL for c in cards),
            incomplete=sum(c.state == ServerState.INCOMPLETE for c in cards),
            outdated=sum(c.state == ServerState.OUTDATED for c in cards),
            unknown=sum(c.state == ServerState.UNKNOWN for c in cards),
        )

    def _build_server_card(
        self,
        server: int,
    ) -> ServerCard:
        validation = self._validator.validate(
            ServerValidationInput(
                alliance_ranks=list(range(1, 11)),
                thp_ranks=list(range(1, 11)),
            )
        )

        rankings = self._ranking.analyze(server)
        intelligence = self._intelligence.analyze(server)

        recruitability = 0.0

        if rankings.recruitment.entries:
            recruitability = rankings.recruitment.entries[0].score

        growth = 0.0

        if rankings.growth.entries:
            growth = max(
                rankings.growth.entries[0].score,
                0.0,
            )

        risk = min(
            len(intelligence.assessment.risks) * 12,
            100,
        )

        state = (
            ServerState.READY
            if validation.status == ValidationStatus.PASSED
            else ServerState.INCOMPLETE
        )

        return ServerCard(
            server=server,
            state=state,
            dataset_quality=validation.quality_score,
            activity=growth,
            recruitability=recruitability,
            risk=risk,
            last_snapshot="Latest snapshot",
            summary=validation.summary,
            assessment_available=validation.status == ValidationStatus.PASSED,
        )