"""
LastWarIntel
Insight Rules
Version: 1.1

Rule set generating high-level insights from SignalContext.
"""

from __future__ import annotations

from analytics.events.models import Severity
from analytics.intelligence.models import (
    Insight,
    InsightCategory,
    InsightPriority,
)
from analytics.signals.models import SignalContext


class InsightRuleEngine:
    """
    Evaluates SignalContext and produces strategic insights.
    """

    def evaluate(self, signals: SignalContext) -> list[Insight]:
        insights: list[Insight] = []

        insights.extend(self._strong_server(signals))
        insights.extend(self._internal_restructuring(signals))
        insights.extend(self._recruitment_opportunity(signals))
        insights.extend(self._rapid_alliance_growth(signals))
        insights.extend(self._high_volatility(signals))
        insights.extend(self._weak_server(signals))
        insights.extend(self._healthy_environment(signals))

        return insights

    @staticmethod
    def _strong_server(signals: SignalContext) -> list[Insight]:
        if not (signals.overall >= 70 and signals.growth >= 10):
            return []

        return [
            Insight(
                title="Strong Server",
                summary="Server remains one of the strongest and continues to grow.",
                confidence=94,
                severity=Severity.LOW,
                category=InsightCategory.GROWTH,
                priority=InsightPriority.MEDIUM,
                recommendation="Maintain current strategic direction.",
                evidence=[
                    f"Overall score: {signals.overall:.2f}",
                    f"Growth: {signals.growth:.2f}%",
                ],
            )
        ]

    @staticmethod
    def _internal_restructuring(signals: SignalContext) -> list[Insight]:
        if not (
            signals.left_top10_count >= 2
            and signals.critical_alliances >= 2
        ):
            return []

        return [
            Insight(
                title="Internal Restructuring",
                summary=(
                    "Multiple alliances disappeared after transfer, "
                    "indicating internal restructuring."
                ),
                confidence=96,
                severity=Severity.HIGH,
                category=InsightCategory.RISK,
                priority=InsightPriority.HIGH,
                recommendation="Increase diplomatic activity and monitor leadership movement.",
                evidence=[
                    f"{signals.left_top10_count} alliances left the latest Top10.",
                    f"{signals.critical_alliances} alliances are currently critical.",
                ],
            )
        ]

    @staticmethod
    def _recruitment_opportunity(signals: SignalContext) -> list[Insight]:
        if signals.immediate_targets < 2:
            return []

        return [
            Insight(
                title="Recruitment Opportunity",
                summary="Several high-value recruitment targets have been detected.",
                confidence=92,
                severity=Severity.MEDIUM,
                category=InsightCategory.RECRUITMENT,
                priority=InsightPriority.HIGH,
                recommendation="Contact alliance leadership before competitors do.",
                evidence=[
                    f"{signals.immediate_targets} immediate recruitment targets.",
                ],
            )
        ]

    @staticmethod
    def _rapid_alliance_growth(signals: SignalContext) -> list[Insight]:
        if signals.large_power_gain_count < 2:
            return []

        return [
            Insight(
                title="Alliance Growth",
                summary="Multiple alliances are growing rapidly.",
                confidence=90,
                severity=Severity.LOW,
                category=InsightCategory.COMPETITION,
                priority=InsightPriority.MEDIUM,
                recommendation="Monitor emerging competitors.",
                evidence=[
                    f"{signals.large_power_gain_count} alliances gained significant power.",
                ],
            )
        ]

    @staticmethod
    def _high_volatility(signals: SignalContext) -> list[Insight]:
        if signals.volatility < 10:
            return []

        return [
            Insight(
                title="High Volatility",
                summary="Unusually high alliance movement detected.",
                confidence=88,
                severity=Severity.MEDIUM,
                category=InsightCategory.RISK,
                priority=InsightPriority.MEDIUM,
                recommendation="Observe transfer activity closely.",
                evidence=[
                    f"Volatility: {signals.volatility:.2f}%",
                ],
            )
        ]

    @staticmethod
    def _weak_server(signals: SignalContext) -> list[Insight]:
        if signals.overall >= 40:
            return []

        return [
            Insight(
                title="Weak Server",
                summary="Server has become strategically weak.",
                confidence=87,
                severity=Severity.HIGH,
                category=InsightCategory.RISK,
                priority=InsightPriority.HIGH,
                recommendation="Recruit selectively. Focus on strong individual players.",
                evidence=[
                    f"Overall score: {signals.overall:.2f}",
                ],
            )
        ]

    @staticmethod
    def _healthy_environment(signals: SignalContext) -> list[Insight]:
        if not (
            signals.critical_alliances == 0
            and signals.growth >= 10
            and signals.volatility < 8
        ):
            return []

        return [
            Insight(
                title="Healthy Environment",
                summary="Growth appears healthy without signs of instability.",
                confidence=91,
                severity=Severity.LOW,
                category=InsightCategory.STABILITY,
                priority=InsightPriority.LOW,
                recommendation="Maintain diplomatic relationships.",
                evidence=[
                    "No critical alliances detected.",
                    f"Growth: {signals.growth:.2f}%",
                    f"Volatility: {signals.volatility:.2f}%",
                ],
            )
        ]