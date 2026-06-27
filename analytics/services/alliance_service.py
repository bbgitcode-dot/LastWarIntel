"""
Alliance Service
"""

from __future__ import annotations

from analytics.application.entity_report_builder import (
    EntityReportBuilder,
)


class AllianceService:
    """
    Provides alliance intelligence reports.
    """

    def get_report(
        self,
        server: int,
        alliance: str,
    ):
        return EntityReportBuilder().build(
            server=server,
            alliance=alliance,
        )