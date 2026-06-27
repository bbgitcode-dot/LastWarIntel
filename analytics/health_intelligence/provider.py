"""
Sentinel
Health Indicator Provider
"""

from __future__ import annotations

from analytics.comparison.models import DifferenceSet
from analytics.health_intelligence.facade import (
    HealthIntelligenceFacade,
)
from analytics.intelligence.indicators import StrategicIndicator


class HealthProvider:
    """
    Provides structural health indicators.

    Health is intentionally not an IntelligenceProvider,
    because it produces StrategicIndicators instead of
    IntelligenceFacts.
    """

    @property
    def entity_name(
        self,
    ) -> str:

        return "Health"

    def __init__(
        self,
    ) -> None:

        self._facade = HealthIntelligenceFacade()

    def analyze(
        self,
        differences: DifferenceSet,
    ) -> list[StrategicIndicator]:

        return self._facade.analyze(
            differences,
        ).indicators