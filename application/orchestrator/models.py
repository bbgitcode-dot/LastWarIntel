"""
Sentinel
Orchestrator Models
"""

from __future__ import annotations

from dataclasses import dataclass

from analytics.opportunity_intelligence.models import OpportunityAssessment
from application.briefing.models import MorningBriefing
from application.reports.models import Report
from application.watchlist.models import WatchTarget


@dataclass(slots=True, frozen=True)
class SentinelResult:
    """
    Final result returned by the Sentinel orchestrator.

    During the migration to the MorningBriefing domain,
    legacy properties remain available.
    """

    #
    # New application aggregate
    #
    briefing: MorningBriefing | None = None

    #
    # Legacy compatibility
    #
    opportunities: list[OpportunityAssessment] | None = None

    watch_targets: list[WatchTarget] | None = None

    report: Report | None = None