"""
Sentinel
Morning Briefing Models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from application.assessments.models import Assessment
from application.watchlist.models import WatchTarget


@dataclass(slots=True, frozen=True)
class MorningBriefing:
    """
    High-level operational briefing for a server.

    The MorningBriefing represents everything an alliance
    leader should know when opening Sentinel.
    """

    server: int

    generated_at: datetime

    summary: str

    assessments: list[Assessment] = field(
        default_factory=list,
    )

    breaking_news: list[str] = field(
        default_factory=list,
    )

    watch_targets: list[WatchTarget] = field(
        default_factory=list,
    )