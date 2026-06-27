"""
Sentinel
Cockpit Facade
"""

from __future__ import annotations

from application.cockpit.builder import CockpitBuilder


class CockpitFacade:
    """
    Public entry point for cockpit structure.
    """

    def __init__(
        self,
    ) -> None:

        self._builder = CockpitBuilder()

    def build(
        self,
    ):

        return self._builder.build()