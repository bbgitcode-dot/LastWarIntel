"""
Sentinel
Server Intelligence Recommendation Builder
"""

from __future__ import annotations

from analytics.intelligence.indicators import StrategicIndicator

from application.server_intelligence.models import (
    ServerRecommendation,
    ServerRecommendationPriority,
)


class ServerRecommendationBuilder:
    """
    Builds structured recommendations from strategic indicators.
    """

    def build(
        self,
        indicators: list[StrategicIndicator],
    ) -> ServerRecommendation:

        strategic_risk = self._value(
            indicators,
            "Strategic Risk",
        )

        alliance_stability = self._value(
            indicators,
            "Alliance Stability",
        )

        whale_balance = self._value(
            indicators,
            "Whale Balance",
        )

        transfer_activity = self._value(
            indicators,
            "Transfer Activity",
        )

        if strategic_risk >= 80:
            return ServerRecommendation(
                title="Immediate Leadership Review",
                description=(
                    "Multiple severe instability signals were detected. "
                    "Review the server before making strategic decisions."
                ),
                priority=ServerRecommendationPriority.CRITICAL,
            )

        if strategic_risk >= 55:
            return ServerRecommendation(
                title="Prepare Diplomatic Action",
                description=(
                    "The server shows elevated instability. "
                    "Monitor leadership movement and prepare recruitment outreach."
                ),
                priority=ServerRecommendationPriority.HIGH,
            )

        if whale_balance > 0 and transfer_activity >= 50:
            return ServerRecommendation(
                title="Evaluate Strength Increase",
                description=(
                    "Incoming whale movement suggests increasing strategic strength. "
                    "Verify whether growth is concentrated or broadly distributed."
                ),
                priority=ServerRecommendationPriority.MEDIUM,
            )

        if alliance_stability < 70:
            return ServerRecommendation(
                title="Monitor Alliance Structure",
                description=(
                    "Alliance structure shows early instability. "
                    "Confirm with the next snapshot before acting."
                ),
                priority=ServerRecommendationPriority.MEDIUM,
            )

        return ServerRecommendation(
            title="Continue Monitoring",
            description=(
                "No major server-level action is required. "
                "Continue observing future snapshots."
            ),
            priority=ServerRecommendationPriority.LOW,
        )

    @staticmethod
    def _value(
        indicators: list[StrategicIndicator],
        title: str,
    ) -> float:

        for indicator in indicators:
            if indicator.title == title:
                return indicator.value

        return 0.0