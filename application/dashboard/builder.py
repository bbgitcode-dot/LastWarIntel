"""
LastWarIntel
Dashboard Builder
Version: 1.2

Builds presentation models for the dashboard.
"""

from __future__ import annotations

from analytics.campaign.facade import CampaignFacade
from analytics.ranking.facade import RankingFacade
from analytics.server_intelligence.facade import ServerIntelligenceFacade

from application.dashboard.models import (
    DashboardCampaign,
    DashboardData,
    DashboardFeedItem,
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

    def build(self, server: int) -> DashboardData:
        ranking = self._ranking.analyze(server)
        campaign = self._campaign.transfer(server)
        server_view = self._server.analyze(server)

        recruitment_score = self._recruitment_score(ranking)
        growth_score = self._growth_score(ranking)
        risk_score = self._risk_score(server_view)
        health_score = max(100.0 - risk_score, 0.0)

        metrics = [
            DashboardMetric("Overall Health", health_score),
            DashboardMetric("Recruitment", recruitment_score),
            DashboardMetric("Growth", growth_score, unit="%"),
            DashboardMetric("Strategic Risk", risk_score),
        ]

        return DashboardData(
            server=server,
            status=self._status_from_risk(risk_score),
            snapshot="Latest available snapshot",
            metrics=metrics,
            top_targets=self._build_targets(ranking),
            campaign=self._build_campaign(campaign),
            feed=self._build_feed(server_view),
            outlook=server_view.assessment.outlook.summary,
        )

    @staticmethod
    def _recruitment_score(ranking) -> float:
        if not ranking.recruitment.entries:
            return 0.0
        return float(ranking.recruitment.entries[0].score)

    @staticmethod
    def _growth_score(ranking) -> float:
        if not ranking.growth.entries:
            return 0.0
        return max(float(ranking.growth.entries[0].score), 0.0)

    @staticmethod
    def _risk_score(server_view) -> float:
        risks = server_view.assessment.risks

        if not risks:
            return 0.0

        critical = sum(1 for risk in risks if risk.priority.name == "CRITICAL")
        high = sum(1 for risk in risks if risk.priority.name == "HIGH")
        medium = sum(1 for risk in risks if risk.priority.name == "MEDIUM")

        score = critical * 15 + high * 7 + medium * 3

        return min(float(score), 100.0)

    @staticmethod
    def _status_from_risk(risk_score: float) -> str:
        if risk_score >= 75:
            return "Critical Window"
        if risk_score >= 50:
            return "High Activity"
        if risk_score >= 25:
            return "Monitoring"
        return "Operational"

    @staticmethod
    def _build_targets(ranking) -> list[DashboardTarget]:
        return [
            DashboardTarget(
                alliance=entry.alliance,
                priority=entry.score,
                confidence=entry.confidence,
                summary=entry.summary,
            )
            for entry in ranking.recruitment.entries[:5]
        ]

    @staticmethod
    def _build_campaign(campaign) -> DashboardCampaign:
        phase_count = len(campaign.campaign.phases)

        target_count = sum(
            len(phase.targets)
            for phase in campaign.campaign.phases
        )

        next_action = "No immediate action."

        if campaign.campaign.phases and campaign.campaign.phases[0].targets:
            first_target = campaign.campaign.phases[0].targets[0]
            next_action = f"Contact {first_target.alliance}"

        progress = min(100.0, 35.0 + target_count * 15.0) if phase_count else 0.0
        estimated_success = min(100.0, 70.0 + target_count * 8.0)

        return DashboardCampaign(
            summary=campaign.campaign.summary,
            phase_count=phase_count,
            target_count=target_count,
            next_action=next_action,
            progress=progress,
            estimated_success=estimated_success,
        )

    @staticmethod
    def _build_feed(server_view) -> list[DashboardFeedItem]:
        feed: list[DashboardFeedItem] = []

        for risk in server_view.assessment.risks[:3]:
            feed.append(
                DashboardFeedItem(
                    title=risk.title,
                    summary=risk.summary,
                    severity="critical"
                    if risk.priority.name == "CRITICAL"
                    else "warning",
                    timestamp="Latest snapshot",
                )
            )

        for opportunity in server_view.assessment.opportunities[:3]:
            feed.append(
                DashboardFeedItem(
                    title=opportunity.title,
                    summary=opportunity.summary,
                    severity="success",
                    timestamp="Latest snapshot",
                )
            )

        if not feed:
            feed.append(
                DashboardFeedItem(
                    title="No major intelligence events",
                    summary="No critical server-level changes detected.",
                    severity="info",
                    timestamp="Latest snapshot",
                )
            )

        return feed[:5]