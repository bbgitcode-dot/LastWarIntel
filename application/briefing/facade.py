"""
Sentinel
Morning Briefing Facade
"""

from __future__ import annotations

from datetime import datetime

from application.briefing.builder import MorningBriefingBuilder
from application.briefing.models import MorningBriefing
from application.watchlist.models import WatchTarget


class MorningBriefingFacade:
    """
    Public entry point for creating operational morning briefings.
    """

    def __init__(self) -> None:
        self._builder = MorningBriefingBuilder()

    def create(
        self,
        *,
        server: int,
        watch_targets: list[WatchTarget],
        breaking_news: list[str] | None = None,
        generated_at: datetime | None = None,
    ) -> MorningBriefing:

        return self._builder.build(
            server=server,
            watch_targets=watch_targets,
            breaking_news=breaking_news,
            generated_at=generated_at,
        )