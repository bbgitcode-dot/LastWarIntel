"""
Sentinel
Server Intelligence Indicator Builder
"""

from __future__ import annotations

from analytics.reasoning.models import IntelligenceFact

from application.server_intelligence.models import (
    ServerStrategicIndicator,
)


class ServerIndicatorBuilder:
    """
    Builds strategic indicators from IntelligenceFacts.
    """

    def build(
        self,
        facts: list[IntelligenceFact],
    ) -> list[ServerStrategicIndicator]:

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

        strategic_risk = min(
            alliance_power_drops * 35
            + alliance_disappeared * 25
            + outgoing_whales * 30,
            100,
        )

        transfer_activity = min(
            whale_transfers * 35
            + incoming_whales * 25
            + outgoing_whales * 25,
            100,
        )

        whale_balance = incoming_whales - outgoing_whales

        alliance_stability = max(
            0,
            100
            - alliance_power_drops * 30
            - alliance_disappeared * 25,
        )

        return [
            ServerStrategicIndicator(
                title="Whale Balance",
                value=whale_balance,
                unit="",
                summary=(
                    f"{incoming_whales} incoming, "
                    f"{outgoing_whales} outgoing whale signal(s)."
                ),
            ),
            ServerStrategicIndicator(
                title="Transfer Activity",
                value=transfer_activity,
                unit="",
                summary=(
                    f"{whale_transfers} whale transfer signal(s) detected."
                ),
            ),
            ServerStrategicIndicator(
                title="Alliance Stability",
                value=alliance_stability,
                unit="%",
                summary=(
                    f"{alliance_power_drops} power drop signal(s), "
                    f"{alliance_disappeared} disappeared alliance signal(s), "
                    f"{alliance_appeared} appeared alliance signal(s)."
                ),
            ),
            ServerStrategicIndicator(
                title="Strategic Risk",
                value=strategic_risk,
                unit="",
                summary="Risk derived from whale losses and alliance instability.",
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