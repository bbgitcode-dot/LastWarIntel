"""
Sentinel
Whale Analyzer
"""

from __future__ import annotations

from analytics.comparison.difference import (
    Difference,
    DifferenceType,
    EntityType,
)
from analytics.comparison.models import DifferenceSet
from analytics.whale.models import (
    WhaleAssessment,
    WhaleEvent,
)


class WhaleAnalyzer:
    """
    Detect whale movements based on generic differences.
    """

    #
    # Temporary threshold.
    # Later configurable per campaign/server.
    #
    THRESHOLD = 220.0

    def analyze(
        self,
        differences: DifferenceSet,
    ) -> WhaleAssessment:

        events: list[WhaleEvent] = []

        incoming = 0
        outgoing = 0
        moved = 0

        for difference in differences.by_entity(EntityType.PLAYER):
            power = self._extract_power(
                difference,
            )

            if not self._is_whale(power):
                continue

            if difference.difference_type == DifferenceType.ADDED:
                incoming += 1
                event = "Incoming"

            elif difference.difference_type == DifferenceType.REMOVED:
                outgoing += 1
                event = "Outgoing"

            elif difference.difference_type == DifferenceType.MOVED:
                moved += 1
                event = "Moved"

            else:
                continue

            events.append(
                WhaleEvent(
                    identifier=difference.identifier,
                    event=event,
                    power=power,
                    confidence=difference.confidence,
                    payload=difference.payload,
                )
            )

        return WhaleAssessment(
            whales=events,
            incoming=incoming,
            outgoing=outgoing,
            moved=moved,
        )

    def _is_whale(
        self,
        power: float | None,
    ) -> bool:

        return (
            power is not None
            and power >= self.THRESHOLD
        )

    @staticmethod
    def _extract_power(
        difference: Difference,
    ) -> float | None:

        if "power" in difference.payload:
            return difference.payload.get("power")

        changes = difference.payload.get(
            "changes",
            {},
        )

        if "power" in changes:
            return changes["power"][1]

        return None