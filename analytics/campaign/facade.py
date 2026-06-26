"""
LastWarIntel
Campaign Facade
Version: 1.0

High-level API for campaign planning.
"""

from __future__ import annotations

from dataclasses import dataclass

from analytics.campaign.models import Campaign
from analytics.campaign.planner import CampaignPlanner


@dataclass(slots=True, frozen=True)
class CampaignResult:
    """
    Result returned by the Campaign domain.
    """

    campaign: Campaign


class CampaignFacade:
    """
    High-level API for campaign planning.
    """

    def __init__(self) -> None:
        self._planner = CampaignPlanner()

    def transfer(
        self,
        server: int,
    ) -> CampaignResult:
        """
        Builds a transfer campaign.
        """

        return CampaignResult(
            campaign=self._planner.transfer_campaign(server),
        )