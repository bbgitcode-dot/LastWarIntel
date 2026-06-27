"""
Sentinel
Server Overview Builder
"""

from __future__ import annotations

from analytics.ranking.facade import RankingFacade
from analytics.server_intelligence.facade import ServerIntelligenceFacade

from application.server_overview.models import (
    ServerOverviewAlliance,
    ServerOverviewData,
    ServerOverviewMetric,
)


class ServerOverviewBuilder:
    """
    Builds the server overview presentation model.
    """

    def __init__(self) -> None:
        self._ranking = RankingFacade()
        self._server_intelligence = ServerIntelligenceFacade()

    def build(
        self,
        server: int,
    ) -> ServerOverviewData:
        rankings = self._ranking.analyze(server)
        intelligence = self._server_intelligence.analyze(server)

        recruitment_score = 0.0

        if rankings.recruitment.entries:
            recruitment_score = rankings.recruitment.entries[0].score

        growth_score = 0.0

        if rankings.growth.entries:
            growth_score = max(
                rankings.growth.entries[0].score,
                0.0,
            )

        risk_score = min(
            len(intelligence.assessment.risks) * 12,
            100,
        )

        opportunity_score = min(
            len(intelligence.assessment.opportunities) * 14,
            100,
        )

        metrics = [
            ServerOverviewMetric(
                title="Recruitment",
                value=recruitment_score,
            ),
            ServerOverviewMetric(
                title="Growth",
                value=growth_score,
                unit="%",
            ),
            ServerOverviewMetric(
                title="Strategic Risk",
                value=risk_score,
            ),
            ServerOverviewMetric(
                title="Opportunity",
                value=opportunity_score,
            ),
        ]

        recruitment_targets = [
            ServerOverviewAlliance(
                alliance=entry.alliance,
                score=entry.score,
                summary=entry.summary,
                confidence=entry.confidence,
            )
            for entry in rankings.recruitment.entries[:8]
        ]

        growth_leaders = [
            ServerOverviewAlliance(
                alliance=entry.alliance,
                score=entry.score,
                summary=entry.summary,
                confidence=entry.confidence,
            )
            for entry in rankings.growth.entries[:8]
        ]

        return ServerOverviewData(
            server=server,
            status=self._status_from_risk(risk_score),
            metrics=metrics,
            recruitment_targets=recruitment_targets,
            growth_leaders=growth_leaders,
            risks=[
                risk.summary
                for risk in intelligence.assessment.risks[:5]
            ],
            opportunities=[
                opportunity.summary
                for opportunity in intelligence.assessment.opportunities[:5]
            ],
            outlook=intelligence.assessment.outlook.summary,
        )

    @staticmethod
    def _status_from_risk(
        risk_score: float,
    ) -> str:
        if risk_score >= 75:
            return "Critical Window"

        if risk_score >= 50:
            return "High Activity"

        if risk_score >= 25:
            return "Monitoring"

        return "Operational"