"""
LastWarIntel
Campaign Planner
Version: 1.0

Builds strategic campaigns from existing intelligence.
"""

from __future__ import annotations

from analytics.campaign.models import (
    Campaign,
    CampaignPhase,
    CampaignPriority,
    CampaignRisk,
    CampaignTarget,
    CampaignType,
)
from analytics.ranking.facade import RankingFacade
from analytics.server_intelligence.facade import (
    ServerIntelligenceFacade,
)


class CampaignPlanner:
    """
    Creates campaign plans from existing intelligence.
    """

    def __init__(self) -> None:
        self._ranking = RankingFacade()
        self._server = ServerIntelligenceFacade()

    def transfer_campaign(
        self,
        server: int,
    ) -> Campaign:

        ranking = self._ranking.recruitment(server)
        server_view = self._server.analyze(server)

        phase1_targets: list[CampaignTarget] = []
        phase2_targets: list[CampaignTarget] = []

        #
        # Phase assignment
        #

        for entry in ranking.entries:

            if entry.score >= 90:

                phase1_targets.append(
                    CampaignTarget(
                        alliance=entry.alliance,
                        priority=CampaignPriority.CRITICAL,
                        score=entry.score,
                        confidence=entry.confidence,
                        summary=entry.summary,
                        rationale=[
                            "Highest recruitment priority.",
                            "Immediate contact recommended.",
                        ],
                    )
                )

            elif entry.score >= 70:

                phase2_targets.append(
                    CampaignTarget(
                        alliance=entry.alliance,
                        priority=CampaignPriority.HIGH,
                        score=entry.score,
                        confidence=entry.confidence,
                        summary=entry.summary,
                        rationale=[
                            "Strong recruitment candidate.",
                            "Contact after Phase 1.",
                        ],
                    )
                )

        phases = []

        if phase1_targets:
            phases.append(
                CampaignPhase(
                    title="Phase 1 - Immediate Contact",
                    targets=phase1_targets,
                )
            )

        if phase2_targets:
            phases.append(
                CampaignPhase(
                    title="Phase 2 - Follow-up",
                    targets=phase2_targets,
                )
            )

        risks = [
            CampaignRisk(
                title="Competing Recruiters",
                description=(
                    "High-value targets may receive offers from multiple servers."
                ),
                confidence=85,
            )
        ]

        if server_view.assessment.risks:
            risks.append(
                CampaignRisk(
                    title="Server Instability",
                    description=server_view.assessment.outlook.summary,
                    confidence=server_view.assessment.outlook.confidence,
                )
            )

        return Campaign(
            campaign_type=CampaignType.TRANSFER,
            server=server,
            score=90,
            confidence=90,
            summary=(
                "Transfer campaign generated from current recruitment intelligence."
            ),
            phases=phases,
            risks=risks,
        )