"""
LastWarIntel
Dashboard Builder
Version: 1.0

Builds presentation models for the dashboard.
"""

from __future__ import annotations

from analytics.campaign.facade import CampaignFacade
from analytics.ranking.facade import RankingFacade
from analytics.server_intelligence.facade import (
    ServerIntelligenceFacade,
)

from application.dashboard.models import (
    DashboardCampaign,
    DashboardData,
    DashboardMetric,
    DashboardTarget,
)


class DashboardBuilder:
    """
    Creates DashboardData from existing application services.
    """

    def __init__(self) -> None:

        self._ranking = RankingFacade()
        self._campaign = CampaignFacade()
        self._server = ServerIntelligenceFacade()

    def build(
        self,
        server: int,
    ) -> DashboardData:

        ranking = self._ranking.analyze(server)
        campaign = self._campaign.transfer(server)
        server_view = self._server.analyze(server)

        #
        # Metrics
        #

        recruitment_score = 0.0

        if ranking.recruitment.entries:
            recruitment_score = ranking.recruitment.entries[0].score

        growth_score = 0.0

        if ranking.growth.entries:
            growth_score = ranking.growth.entries[0].score

        risk_score = min(
            len(server_view.assessment.risks) * 20,
            100,
        )

        health_score = max(
            100 - risk_score,
            0,
        )

        metrics = [
            DashboardMetric(
                title="Overall Health",
                value=health_score,
            ),
            DashboardMetric(
                title="Recruitment",
                value=recruitment_score,
            ),
            DashboardMetric(
                title="Growth",
                value=growth_score,
            ),
            DashboardMetric(
                title="Strategic Risk",
                value=risk_score,
            ),
        ]

        #
        # Top Targets
        #

        targets: list[DashboardTarget] = []

        for entry in ranking.recruitment.entries[:5]:

            targets.append(
                DashboardTarget(
                    alliance=entry.alliance,
                    priority=entry.score,
                    confidence=entry.confidence,
                    summary=entry.summary,
                )
            )

        #
        # Campaign
        #

        campaign_view = DashboardCampaign(
            summary=campaign.campaign.summary,
            phase_count=len(campaign.campaign.phases),
            target_count=sum(
                len(phase.targets)
                for phase in campaign.campaign.phases
            ),
        )

        return DashboardData(
            server=server,
            metrics=metrics,
            top_targets=targets,
            campaign=campaign_view,
            outlook=server_view.assessment.outlook.summary,
        )