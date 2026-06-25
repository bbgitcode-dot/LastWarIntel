"""
LastWarIntel
Entity Report Builder
Version: 1.0

Application-layer builder for one alliance intelligence report.

This builder orchestrates domain facades and returns an EntityReport.
It does not format, print or calculate domain internals.
"""

from __future__ import annotations

from analytics.application.models import EntityReport
from analytics.events.facade import EventsFacade
from analytics.health.facade import HealthFacade
from analytics.recruitment.facade import RecruitmentFacade
from analytics.timeline.facade import TimelineFacade


class EntityReportBuilder:
    """
    Builds an EntityReport for one alliance on one server.
    """

    def __init__(self) -> None:
        self._timeline = TimelineFacade()
        self._health = HealthFacade()
        self._recruitment = RecruitmentFacade()
        self._events = EventsFacade()

    def build(
        self,
        server: int,
        alliance: str,
    ) -> EntityReport:
        timeline = self._timeline.analyze(server, alliance)
        health = self._health.analyze(server, alliance)
        recruitment = self._recruitment.analyze(server, alliance)
        events = self._events.analyze(server, alliance)

        return EntityReport(
            server=server,
            alliance=alliance,
            timeline=timeline,
            health=health,
            recruitment=recruitment,
            events=events,
        )