"""
Sentinel
Server Intelligence Builder
"""

from __future__ import annotations

from analytics.intelligence.repository import IntelligenceRepository
from analytics.reasoning.models import FactSeverity

from application.server_intelligence.indicator_builder import (
    ServerIndicatorBuilder,
)
from application.server_intelligence.models import (
    ServerIntelligenceAssessment,
)
from application.server_intelligence.recommendation_builder import (
    ServerRecommendationBuilder,
)


class ServerIntelligenceBuilder:
    """
    Builds a strategic server assessment from IntelligenceFacts.
    """

    def __init__(self) -> None:
        self._indicator_builder = ServerIndicatorBuilder()
        self._recommendation_builder = ServerRecommendationBuilder()

    def build(
        self,
        server: int,
        repository: IntelligenceRepository,
    ) -> ServerIntelligenceAssessment:

        facts = repository.all()

        indicators = self._indicator_builder.build(
            facts,
        )

        recommendation = self._recommendation_builder.build(
            indicators,
        )

        critical_facts = [
            fact
            for fact in facts
            if fact.severity == FactSeverity.CRITICAL
        ]

        high_facts = [
            fact
            for fact in facts
            if fact.severity == FactSeverity.HIGH
        ]

        status = self._status_from_indicators(
            indicators,
        )

        return ServerIntelligenceAssessment(
            server=server,
            status=status,
            indicators=indicators,
            recommendation=recommendation,
            critical_facts=critical_facts,
            high_facts=high_facts,
            facts=facts,
        )

    @staticmethod
    def _status_from_indicators(
        indicators,
    ) -> str:

        strategic_risk = 0.0

        for indicator in indicators:
            if indicator.title == "Strategic Risk":
                strategic_risk = indicator.value
                break

        if strategic_risk >= 80:
            return "Critical"

        if strategic_risk >= 55:
            return "High Risk"

        if strategic_risk >= 25:
            return "Monitoring"

        return "Stable"