"""
LastWarIntel
Entity Report Builder
Version: 1.3

Builds a complete EntityReport by orchestrating all analytics domains.
"""

from __future__ import annotations

from analytics.application.models import EntityReport
from analytics.events.facade import EventsFacade
from analytics.health.facade import HealthFacade
from analytics.intelligence.facade import IntelligenceFacade
from analytics.recruitment.facade import RecruitmentFacade
from analytics.situation.facade import SituationFacade
from analytics.timeline.facade import TimelineFacade


class EntityReportBuilder:
    """
    Builds a complete alliance intelligence report.
    """

    def __init__(self) -> None:

        self._timeline = TimelineFacade()
        self._events = EventsFacade()
        self._health = HealthFacade()
        self._recruitment = RecruitmentFacade()
        self._situation = SituationFacade()
        self._intelligence = IntelligenceFacade()

    def build(
        self,
        server: int,
        alliance: str,
    ) -> EntityReport:

        timeline = self._timeline.analyze(server, alliance)

        events = self._events.analyze(server, alliance)

        health = self._health.analyze(server, alliance)

        recruitment = self._recruitment.analyze(server, alliance)

        #
        # Build preliminary report
        #

        report = EntityReport(
            server=server,
            alliance=alliance,
            timeline=timeline,
            events=events,
            health=health,
            recruitment=recruitment,
            situation=None,
            intelligence=None,
        )

        #
        # Situation
        #

        situation = self._situation.analyze(report)

        report = EntityReport(
            server=server,
            alliance=alliance,
            timeline=timeline,
            events=events,
            health=health,
            recruitment=recruitment,
            situation=situation,
            intelligence=None,
        )

        #
        # Intelligence
        #

        intelligence = self._intelligence.analyze(report)

        return EntityReport(
            server=server,
            alliance=alliance,
            timeline=timeline,
            events=events,
            health=health,
            recruitment=recruitment,
            situation=situation,
            intelligence=intelligence,
        )