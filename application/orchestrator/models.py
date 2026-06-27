"""
Sentinel
Orchestrator Models
"""

from __future__ import annotations

from dataclasses import dataclass

from analytics.opportunity_intelligence.models import OpportunityAssessment
from application.reports.models import Report
from application.watchlist.models import WatchTarget


@dataclass(slots=True, frozen=True)
class SentinelResult:
    """
    Final result returned by the Sentinel orchestrator.
    """

    opportunities: list[OpportunityAssessment]

    watch_targets: list[WatchTarget]

    report: Report