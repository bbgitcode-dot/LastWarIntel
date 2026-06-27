"""
Sentinel
Morning Briefing Builder
"""

from __future__ import annotations

from datetime import datetime

from application.assessments.models import Assessment
from application.briefing.models import MorningBriefing
from application.watchlist.models import WatchTarget


class MorningBriefingBuilder:
    """
    Builds a high-level operational morning briefing.

    The builder intentionally performs no business reasoning.
    It aggregates already prepared application objects into a
    single briefing model.
    """

    def build(
        self,
        *,
        server: int,
        assessments: list[Assessment],
        watch_targets: list[WatchTarget],
        breaking_news: list[str] | None = None,
        generated_at: datetime | None = None,
    ) -> MorningBriefing:

        breaking_news = breaking_news or []

        if generated_at is None:
            generated_at = datetime.now()

        return MorningBriefing(
            server=server,
            generated_at=generated_at,
            summary=self._summary(
                assessments,
                watch_targets,
                breaking_news,
            ),
            assessments=assessments,
            breaking_news=breaking_news,
            watch_targets=watch_targets,
        )

    @staticmethod
    def _summary(
        assessments: list[Assessment],
        watch_targets: list[WatchTarget],
        breaking_news: list[str],
    ) -> str:

        return (
            f"{len(assessments)} assessment(s), "
            f"{len(watch_targets)} watch target(s), "
            f"{len(breaking_news)} breaking news item(s)."
        )