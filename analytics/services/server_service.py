"""
Sentinel
Server Service
"""

from __future__ import annotations

from application.server_overview.builder import ServerOverviewBuilder


class ServerService:
    """
    Provides server-level application data.
    """

    def overview(
        self,
        server: int,
    ):
        return ServerOverviewBuilder().build(
            server=server,
        )