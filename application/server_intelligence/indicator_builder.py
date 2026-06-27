"""
Sentinel
Server Intelligence Indicator Builder
"""

from __future__ import annotations

from analytics.intelligence.indicator_builder import (
    StrategicIndicatorBuilder,
)
from analytics.intelligence.indicators import StrategicIndicator
from analytics.reasoning.models import IntelligenceFact


class ServerIndicatorBuilder:
    """
    Compatibility wrapper for server indicators.

    Server-specific views use this builder while the actual
    indicator logic lives in analytics.intelligence.
    """

    def __init__(self) -> None:
        self._builder = StrategicIndicatorBuilder()

    def build(
        self,
        facts: list[IntelligenceFact],
    ) -> list[StrategicIndicator]:

        return self._builder.build_server_indicators(
            facts,
        )