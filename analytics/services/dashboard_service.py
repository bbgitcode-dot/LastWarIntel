"""
Dashboard Service
"""

from __future__ import annotations

from application.dashboard.builder import DashboardBuilder


class DashboardService:
    """
    Provides dashboard data.
    """

    def get_dashboard(
        self,
        server: int,
    ):
        return DashboardBuilder().build(
            server=server,
        )