"""
LastWarIntel
Insight Rules
Version: 1.0

Rule set generating high-level insights from SignalContext.
"""

from __future__ import annotations

from analytics.events.models import Severity
from analytics.intelligence.models import Insight
from analytics.signals.models import SignalContext


class InsightRuleEngine:

    def evaluate(self, signals: SignalContext) -> list[Insight]:

        insights: list[Insight] = []

        # -------------------------------------------------------------
        # Strong Server
        # -------------------------------------------------------------

        if signals.overall >= 70 and signals.growth >= 10:

            insights.append(
                Insight(
                    title="Strong Server",
                    summary="Server remains one of the strongest and continues to grow.",
                    confidence=94,
                    severity=Severity.LOW,
                    recommendation="Maintain current strategic direction.",
                    evidence=[
                        f"Overall score: {signals.overall:.2f}",
                        f"Growth: {signals.growth:.2f}%",
                    ],
                )
            )

        # -------------------------------------------------------------
        # Internal Restructuring
        # -------------------------------------------------------------

        if (
            signals.left_top10_count >= 2
            and signals.critical_alliances >= 2
        ):

            insights.append(
                Insight(
                    title="Internal Restructuring",
                    summary="Multiple alliances disappeared after transfer, indicating internal restructuring.",
                    confidence=96,
                    severity=Severity.HIGH,
                    recommendation="Increase diplomatic activity and monitor leadership movement.",
                    evidence=[
                        f"{signals.left_top10_count} alliances left the latest Top10.",
                        f"{signals.critical_alliances} alliances are currently critical.",
                    ],
                )
            )

        # -------------------------------------------------------------
        # Recruitment Opportunity
        # -------------------------------------------------------------

        if signals.immediate_targets >= 2:

            insights.append(
                Insight(
                    title="Recruitment Opportunity",
                    summary="Several high-value recruitment targets have been detected.",
                    confidence=92,
                    severity=Severity.MEDIUM,
                    recommendation="Contact alliance leadership before competitors do.",
                    evidence=[
                        f"{signals.immediate_targets} immediate recruitment targets.",
                    ],
                )
            )

        # -------------------------------------------------------------
        # Rapid Alliance Growth
        # -------------------------------------------------------------

        if signals.large_power_gain_count >= 2:

            insights.append(
                Insight(
                    title="Alliance Growth",
                    summary="Multiple alliances are growing rapidly.",
                    confidence=90,
                    severity=Severity.LOW,
                    recommendation="Monitor emerging competitors.",
                    evidence=[
                        f"{signals.large_power_gain_count} alliances gained significant power.",
                    ],
                )
            )

        # -------------------------------------------------------------
        # High Volatility
        # -------------------------------------------------------------

        if signals.volatility >= 10:

            insights.append(
                Insight(
                    title="High Volatility",
                    summary="Unusually high alliance movement detected.",
                    confidence=88,
                    severity=Severity.MEDIUM,
                    recommendation="Observe transfer activity closely.",
                    evidence=[
                        f"Volatility: {signals.volatility:.2f}%",
                    ],
                )
            )

        # -------------------------------------------------------------
        # Weak Server
        # -------------------------------------------------------------

        if signals.overall < 40:

            insights.append(
                Insight(
                    title="Weak Server",
                    summary="Server has become strategically weak.",
                    confidence=87,
                    severity=Severity.HIGH,
                    recommendation="Recruit selectively. Focus on strong individual players.",
                    evidence=[
                        f"Overall score: {signals.overall:.2f}",
                    ],
                )
            )

        # -------------------------------------------------------------
        # Healthy Stability
        # -------------------------------------------------------------

        if (
            signals.critical_alliances == 0
            and signals.growth >= 10
            and signals.volatility < 8
        ):

            insights.append(
                Insight(
                    title="Healthy Environment",
                    summary="Growth appears healthy without signs of instability.",
                    confidence=91,
                    severity=Severity.LOW,
                    recommendation="Maintain diplomatic relationships.",
                    evidence=[
                        "No critical alliances detected.",
                        f"Growth: {signals.growth:.2f}%",
                        f"Volatility: {signals.volatility:.2f}%",
                    ],
                )
            )

        return insights