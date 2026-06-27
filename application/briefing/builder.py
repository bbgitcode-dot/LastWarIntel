"""
Sentinel
Morning Briefing Builder
"""

from __future__ import annotations

from datetime import datetime

from application.briefing.models import MorningBriefing
from application.watchlist.models import WatchTarget


class MorningBriefingBuilder:
    """
    Builds a high-level operational morning briefing.

    The builder aggregates operational objects into a single
    MorningBriefing without performing business reasoning.
    """

    def build(
        self,
        *,
        server: int,
        watch_targets: list[WatchTarget],
        breaking_news: list[str] | None = None,
        generated_at: datetime | None = None,
    ) -> MorningBriefing:

        breaking_news = breaking_news or []

        if generated_at is None:
            generated_at = datetime.now()

        assessments = [
            target.assessment
            for target in watch_targets
            if target.assessment is not None
        ]

        return MorningBriefing(
            server=server,
            generated_at=generated_at,
            summary=self._summary(
                assessments=len(assessments),
                watch_targets=len(watch_targets),
                breaking_news=len(breaking_news),
            ),
            assessments=assessments,
            breaking_news=breaking_news,
            watch_targets=watch_targets,
        )

    @staticmethod
    def _summary(
        *,
        assessments: int,
        watch_targets: int,
        breaking_news: int,
    ) -> str:

        return (
            f"{assessments} assessment(s), "
            f"{watch_targets} watch target(s), "
            f"{breaking_news} breaking news item(s)."
        )