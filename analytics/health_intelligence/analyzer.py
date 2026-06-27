"""
Sentinel
Health Intelligence Analyzer
"""

from __future__ import annotations

from analytics.comparison.difference import DifferenceType
from analytics.comparison.models import DifferenceSet
from analytics.health_intelligence.models import (
    HealthAssessment,
    HealthSignal,
)


class HealthIntelligenceAnalyzer:
    """
    Detects structural instability signals.

    Health does not create facts.
    Health interprets facts/differences into indicators.
    """

    BASE_SCORE = 100

    def analyze(
        self,
        differences: DifferenceSet,
    ) -> HealthAssessment:

        signals: list[HealthSignal] = []

        score = self.BASE_SCORE

        for difference in differences:

            changes = difference.payload.get(
                "changes",
                {},
            )

            if "power" not in changes:
                continue

            before, after = changes["power"]

            if before in (None, 0) or after is None:
                continue

            if after >= before:
                continue

            decline = (before - after) / before

            if decline >= 0.25:
                impact = -35
                title = "Severe Power Decline"
                reason = "Power dropped more than 25%."

            elif decline >= 0.15:
                impact = -20
                title = "Major Power Decline"
                reason = "Power dropped more than 15%."

            elif decline >= 0.08:
                impact = -10
                title = "Moderate Power Decline"
                reason = "Power dropped more than 8%."

            else:
                continue

            signals.append(
                HealthSignal(
                    title=title,
                    impact=impact,
                    confidence=difference.confidence,
                    reason=reason,
                    payload=difference.payload,
                )
            )

            score += impact

            if difference.difference_type == DifferenceType.MOVED:
                signals.append(
                    HealthSignal(
                        title="Organizational Movement",
                        impact=-10,
                        confidence=difference.confidence,
                        reason="Entity changed server or alliance context.",
                        payload=difference.payload,
                    )
                )

                score -= 10

        score = max(
            score,
            0,
        )

        return HealthAssessment(
            score=score,
            signals=signals,
        )