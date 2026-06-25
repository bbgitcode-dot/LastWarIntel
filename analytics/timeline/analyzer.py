"""
LastWarIntel
Timeline Analyzer
Version: 1.0

Builds alliance timelines from historical repository data.
"""

from __future__ import annotations

from services.server_repository import ServerRepository

from analytics.timeline.models import (
    AllianceTimeline,
    TimelinePoint,
)


class TimelineAnalyzer:
    """
    Converts historical alliance snapshots into timeline objects.
    """

    def __init__(self) -> None:
        self._repository = ServerRepository()

    def analyze_server(self, server: int) -> list[AllianceTimeline]:
        """
        Build timelines for every alliance on one server.
        """

        histories = self._repository.get_all_alliance_histories(server)

        timelines: list[AllianceTimeline] = []

        for alliance, history in sorted(histories.items()):

            timeline = AllianceTimeline(
                server=server,
                alliance=alliance,
            )

            #
            # Repository already returns snapshots in chronological order.
            #
            for snapshot in history:

                timeline.points.append(
                    TimelinePoint(
                        collection=snapshot["collection"],
                        rank=snapshot["rank"],
                        power=snapshot["power"],
                    )
                )

            timelines.append(timeline)

        return timelines

    def analyze_alliance(
        self,
        server: int,
        alliance: str,
    ) -> AllianceTimeline | None:
        """
        Build timeline for one alliance.
        """

        histories = self._repository.get_all_alliance_histories(server)

        history = histories.get(alliance)

        if history is None:
            return None

        timeline = AllianceTimeline(
            server=server,
            alliance=alliance,
        )

        for snapshot in history:

            timeline.points.append(
                TimelinePoint(
                    collection=snapshot["collection"],
                    rank=snapshot["rank"],
                    power=snapshot["power"],
                )
            )

        return timeline