"""
LastWarIntel
Server Intelligence Facade
Version: 1.0

High-level API for server intelligence.
"""

from __future__ import annotations

from dataclasses import dataclass

from analytics.server_intelligence.analyzer import (
    ServerIntelligenceAnalyzer,
)
from analytics.server_intelligence.models import (
    ServerStrategicAssessment,
)


@dataclass(slots=True, frozen=True)
class ServerIntelligenceResult:
    """
    Result returned by the Server Intelligence domain.
    """

    assessment: ServerStrategicAssessment


class ServerIntelligenceFacade:
    """
    High-level API for server intelligence.
    """

    def __init__(self) -> None:
        self._analyzer = ServerIntelligenceAnalyzer()

    def analyze(
        self,
        server: int,
    ) -> ServerIntelligenceResult:

        assessment = self._analyzer.analyze(server)

        return ServerIntelligenceResult(
            assessment=assessment,
        )