"""
LastWarIntel
Ranking Analyzer
Version: 1.0

Creates reusable strategic rankings from EntityReports.
"""

from __future__ import annotations

from analytics.application.entity_report_builder import EntityReportBuilder
from analytics.ranking.models import (
    Ranking,
    RankingEntry,
    RankingType,
)
from services.server_repository import ServerRepository


class RankingAnalyzer:
    """
    Creates rankings from all alliance reports of a server.
    """

    def __init__(self) -> None:

        self._repository = ServerRepository()
        self._reports = EntityReportBuilder()

    def recruitment(
        self,
        server: int,
    ) -> Ranking:

        histories = self._repository.get_all_alliance_histories(server)

        entries: list[RankingEntry] = []

        for alliance in sorted(histories.keys()):

            report = self._reports.build(server, alliance)

            if not report.recruitment:
                continue

            target = report.recruitment.target

            entries.append(
                RankingEntry(
                    alliance=alliance,
                    score=target.priority,
                    title=target.recommendation,
                    summary=(
                        f"Recruitment priority "
                        f"{target.priority}/100."
                    ),
                    confidence=target.confidence,
                )
            )

        entries.sort(
            key=lambda entry: (
                -entry.score,
                -entry.confidence,
                entry.alliance,
            )
        )

        return Ranking(
            ranking_type=RankingType.RECRUITMENT,
            entries=entries,
        )

    def growth(
        self,
        server: int,
    ) -> Ranking:

        histories = self._repository.get_all_alliance_histories(server)

        entries: list[RankingEntry] = []

        for alliance in sorted(histories.keys()):

            report = self._reports.build(server, alliance)

            if not report.timeline:
                continue

            metrics = report.timeline.metrics

            entries.append(
                RankingEntry(
                    alliance=alliance,
                    score=metrics.total_growth_percent,
                    title="Growth",
                    summary=(
                        f"{metrics.total_growth_percent:+.2f}% "
                        "overall growth."
                    ),
                    confidence=90,
                )
            )

        entries.sort(
            key=lambda entry: (
                -entry.score,
                entry.alliance,
            )
        )

        return Ranking(
            ranking_type=RankingType.GROWTH,
            entries=entries,
        )