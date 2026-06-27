"""
Sentinel
Application Orchestrator
"""

from __future__ import annotations

from analytics.intelligence.indicators import StrategicIndicator
from analytics.reasoning.models import IntelligenceFact

from application.orchestrator.models import SentinelResult
from application.orchestrator.pipeline import OperationsPipeline


class SentinelOrchestrator:
    """
    Main application entry point.

    This class coordinates all operational
    application services.
    """

    def __init__(
        self,
    ) -> None:

        self._pipeline = OperationsPipeline()

    def execute(
        self,
        server: int,
        alliance: str,
        facts: list[IntelligenceFact],
        indicators: list[StrategicIndicator],
    ) -> SentinelResult:

        return self._pipeline.execute(

            server=server,

            alliance=alliance,

            facts=facts,

            indicators=indicators,

        )