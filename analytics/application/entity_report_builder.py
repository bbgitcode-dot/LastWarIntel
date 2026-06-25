"""
LastWarIntel
Entity Report Builder
Version: 1.1

Builds complete EntityReport objects.
"""

from __future__ import annotations

from analytics.application.models import EntityReport
from analytics.events.facade import EventsFacade
from analytics.health.facade import HealthFacade
from analytics.intelligence.facade import IntelligenceFacade
from analytics.recruitment.facade import RecruitmentFacade
from analytics.timeline.facade import TimelineFacade


class EntityReportBuilder:
    """
    Builds complete entity reports.
    """

    def __init__(self) -> None:

        self._timeline = TimelineFacade()
        self._health = HealthFacade()
        self._recruitment = RecruitmentFacade()
        self._events = EventsFacade()
        self._intelligence = IntelligenceFacade()

    def build(
        self,
        server: int,
        alliance: str,
    ) -> EntityReport:

        timeline = self._timeline.analyze(
            server,
            alliance,
        )

        health = self._health.analyze(
            server,
            alliance,
        )

        recruitment = self._recruitment.analyze(
            server,
            alliance,
        )

        events = self._events.analyze(
            server,
            alliance,
        )

        #
        # Build report without intelligence first.
        #

        report = EntityReport(
            server=server,
            alliance=alliance,
            timeline=timeline,
            health=health,
            recruitment=recruitment,
            events=events,
            intelligence=None,
        )

        #
        # Intelligence depends on the report itself.
        #

        intelligence = self._intelligence.analyze(
            report,
        )

        return EntityReport(
            server=server,
            alliance=alliance,
            timeline=timeline,
            health=health,
            recruitment=recruitment,
            events=events,
            intelligence=intelligence,
        )