"""
Sentinel
Cockpit View Models
"""

from __future__ import annotations

from dataclasses import dataclass, field

from application.assessments.models import Assessment
from application.reports.models import Report
from application.watchlist.models import WatchTarget


@dataclass(slots=True, frozen=True)
class DashboardStatusModel:
    """
    Strategic overview displayed on the dashboard.

    During the migration to the Assessment layer,
    legacy fields remain available to keep the renderer
    backwards compatible.
    """

    watch_target_count: int

    breaking_news_count: int

    server_health: float = 0.0

    recruitment_opportunity: float = 0.0

    assessment: Assessment | None = None

    #
    # Legacy compatibility
    #
    overall_status: str = "Unknown"

    recommendation: str = ""

    confidence: float = 0.0


@dataclass(slots=True, frozen=True)
class PriorityTargetsModel:
    """
    Top priority watch targets.
    """

    targets: list[WatchTarget] = field(
        default_factory=list,
    )


@dataclass(slots=True, frozen=True)
class WatchlistBoardModel:
    """
    Watchlist board.
    """

    targets: list[WatchTarget] = field(
        default_factory=list,
    )


@dataclass(slots=True, frozen=True)
class RecruitmentBoardModel:
    """
    Ranked recruitment targets.
    """

    targets: list[WatchTarget] = field(
        default_factory=list,
    )


@dataclass(slots=True, frozen=True)
class MorningReportModel:
    """
    Morning report presentation model.
    """

    report: Report


@dataclass(slots=True, frozen=True)
class BreakingNewsModel:
    """
    Breaking news presentation model.
    """

    entries: list[str] = field(
        default_factory=list,
    )