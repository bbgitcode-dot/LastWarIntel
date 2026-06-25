"""
LastWarIntel
Health Facade
Version: 1.0

High-level API for alliance health intelligence.
"""

from __future__ import annotations

from dataclasses import dataclass

from analytics.assessment.converter import (
    AllianceHealthAssessmentConverter,
)
from analytics.assessment.models import Assessment
from analytics.health.analyzer import AllianceHealthAnalyzer
from analytics.health.models import AllianceHealth


@dataclass(slots=True)
class HealthResult:
    """
    Complete health intelligence for one alliance.
    """

    health: AllianceHealth
    assessment: Assessment


class HealthFacade:
    """
    High-level API for alliance health.
    """

    def __init__(self) -> None:
        self._analyzer = AllianceHealthAnalyzer()
        self._converter = AllianceHealthAssessmentConverter()

    def analyze(
        self,
        server: int,
        alliance: str,
    ) -> HealthResult | None:

        results = self._analyzer.analyze(server)

        health = next(
            (
                item
                for item in results
                if item.alliance == alliance
            ),
            None,
        )

        if health is None:
            return None

        assessment = self._converter.convert(health)

        return HealthResult(
            health=health,
            assessment=assessment,
        )

    def analyze_server(
        self,
        server: int,
    ) -> list[HealthResult]:

        results: list[HealthResult] = []

        for health in self._analyzer.analyze(server):

            results.append(
                HealthResult(
                    health=health,
                    assessment=self._converter.convert(health),
                )
            )

        return results