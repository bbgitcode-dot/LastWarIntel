"""
Sentinel
Server Landscape Service
"""

from __future__ import annotations

from application.server_landscape.builder import (
    ServerLandscapeBuilder,
)
from application.server_landscape.context import (
    ServerLandscapeContext,
)
from application.server_landscape.models import (
    ServerLandscape,
)


class ServerLandscapeService:
    """
    Provides the Server Landscape application model.
    """

    DEFAULT_SERVERS = [
        638,
        573,
        603,
        556,
        662,
        598,
    ]

    def __init__(self) -> None:

        self._builder = ServerLandscapeBuilder()

    def get_landscape(
        self,
    ) -> ServerLandscape:

        context = ServerLandscapeContext(
            monitored_servers=self.DEFAULT_SERVERS,
        )

        return self._builder.build(
            context=context,
        )