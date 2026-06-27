"""
Sentinel
Strategic Indicator Builder
"""

from __future__ import annotations

from analytics.intelligence.indicators import (
    IndicatorLevel,
    IndicatorScope,
    StrategicIndicator,
)
from analytics.reasoning.models import IntelligenceFact


class StrategicIndicatorBuilder:
    """
    Builds reusable strategic indicators from IntelligenceFacts.
    """

    def build_server_indicators(
        self,
        facts: list[IntelligenceFact],
    ) -> list[StrategicIndicator]:

        incoming_whales = self._count_by_tags(
            facts,
            ["whale", "incoming"],
        )

        outgoing_whales = self._count_by_tags(
            facts,
            ["whale", "outgoing"],
        )

        whale_transfers = self._count_by_tags(
            facts,
            ["whale", "transfer"],
        )

        alliance_power_drops = self._count_by_tags(
            facts,
            ["alliance", "power", "drop"],
        )

        alliance_disappeared = self._count_by_tags(
            facts,
            ["alliance", "disappeared"],
        )

        alliance_appeared = self._count_by_tags(
            facts,
            ["alliance", "appeared"],
        )

        whale_balance = incoming_whales - outgoing_whales

        transfer_activity = min(
            whale_transfers * 35
            + incoming_whales * 25
            + outgoing_whales * 25,
            100,
        )

        alliance_stability = max(
            0,
            100
            - alliance_power_drops * 30
            - alliance_disappeared * 25,
        )

        strategic_risk = min(
            alliance_power_drops * 35
            + alliance_disappeared * 25
            + outgoing_whales * 30,
            100,
        )

        return [
            StrategicIndicator(
                title="Whale Balance",
                value=whale_balance,
                scope=IndicatorScope.SERVER,
                level=self._level_from_balance(
                    whale_balance,
                ),
                summary=(
                    f"{incoming_whales} incoming, "
                    f"{outgoing_whales} outgoing whale signal(s)."
                ),
                tags=["whale", "balance"],
            ),
            StrategicIndicator(
                title="Transfer Activity",
                value=transfer_activity,
                scope=IndicatorScope.SERVER,
                level=self._level_from_score(
                    transfer_activity,
                ),
                summary=(
                    f"{whale_transfers} whale transfer signal(s) detected."
                ),
                tags=["transfer", "activity"],
            ),
            StrategicIndicator(
                title="Alliance Stability",
                value=alliance_stability,
                scope=IndicatorScope.SERVER,
                level=self._inverse_level_from_score(
                    alliance_stability,
                ),
                unit="%",
                summary=(
                    f"{alliance_power_drops} power drop signal(s), "
                    f"{alliance_disappeared} disappeared alliance signal(s), "
                    f"{alliance_appeared} appeared alliance signal(s)."
                ),
                tags=["alliance", "stability"],
            ),
            StrategicIndicator(
                title="Strategic Risk",
                value=strategic_risk,
                scope=IndicatorScope.SERVER,
                level=self._level_from_score(
                    strategic_risk,
                ),
                summary="Risk derived from whale losses and alliance instability.",
                tags=["risk"],
            ),
        ]

    @staticmethod
    def _count_by_tags(
        facts: list[IntelligenceFact],
        required_tags: list[str],
    ) -> int:

        required = {
            tag.casefold()
            for tag in required_tags
        }

        count = 0

        for fact in facts:
            tags = {
                tag.casefold()
                for tag in fact.tags
            }

            if required.issubset(tags):
                count += 1

        return count

    @staticmethod
    def _level_from_score(
        score: float,
    ) -> IndicatorLevel:

        if score >= 80:
            return IndicatorLevel.CRITICAL

        if score >= 55:
            return IndicatorLevel.HIGH

        if score >= 25:
            return IndicatorLevel.MEDIUM

        return IndicatorLevel.LOW

    @staticmethod
    def _inverse_level_from_score(
        score: float,
    ) -> IndicatorLevel:

        if score <= 20:
            return IndicatorLevel.CRITICAL

        if score <= 45:
            return IndicatorLevel.HIGH

        if score <= 70:
            return IndicatorLevel.MEDIUM

        return IndicatorLevel.LOW

    @staticmethod
    def _level_from_balance(
        balance: float,
    ) -> IndicatorLevel:

        if balance <= -3:
            return IndicatorLevel.CRITICAL

        if balance < 0:
            return IndicatorLevel.HIGH

        if balance > 0:
            return IndicatorLevel.MEDIUM

        return IndicatorLevel.LOW