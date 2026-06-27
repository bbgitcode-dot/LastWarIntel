"""
Sentinel
Reports Facade
"""

from __future__ import annotations

from application.reports.builder import ReportBuilder
from application.watchlist.models import WatchTarget


class ReportsFacade:
    """
    Public entry point for Sentinel reports.
    """

    def __init__(
        self,
    ) -> None:

        self._builder = ReportBuilder()

    def morning_report(
        self,
        targets: list[WatchTarget],
    ):

        return self._builder.morning_report(
            targets,
        )