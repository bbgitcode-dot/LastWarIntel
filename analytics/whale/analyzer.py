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
from analytics.reasoning.models import (
    FactEntityType,
    FactSeverity,
    IntelligenceFact,
)
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

        facts = self._build_facts(
            incoming=incoming,
            outgoing=outgoing,
            moved=moved,
            events=events,
        )

        return WhaleAssessment(
            whales=events,
            facts=facts,
            incoming=incoming,
            outgoing=outgoing,
            moved=moved,
        )

    def _build_facts(
        self,
        incoming: int,
        outgoing: int,
        moved: int,
        events: list[WhaleEvent],
    ) -> list[IntelligenceFact]:

        facts: list[IntelligenceFact] = []

        if incoming:
            facts.append(
                IntelligenceFact(
                    source="Whale Intelligence",
                    title="Incoming Whale Movement",
                    description=(
                        f"{incoming} whale player(s) appeared in the current snapshot."
                    ),
                    severity=self._severity_from_count(incoming),
                    confidence=self._average_confidence(events),
                    evidence=[
                        self._format_event(event)
                        for event in events
                        if event.event == "Incoming"
                    ],
                    entity_type=FactEntityType.PLAYER,
                    entity_id="multiple" if incoming > 1 else self._single_entity_id(events, "Incoming"),
                    tags=["whale", "movement", "incoming"],
                )
            )

        if outgoing:
            facts.append(
                IntelligenceFact(
                    source="Whale Intelligence",
                    title="Outgoing Whale Movement",
                    description=(
                        f"{outgoing} whale player(s) disappeared from the current snapshot."
                    ),
                    severity=self._severity_from_count(outgoing),
                    confidence=self._average_confidence(events),
                    evidence=[
                        self._format_event(event)
                        for event in events
                        if event.event == "Outgoing"
                    ],
                    entity_type=FactEntityType.PLAYER,
                    entity_id="multiple" if outgoing > 1 else self._single_entity_id(events, "Outgoing"),
                    tags=["whale", "movement", "outgoing"],
                )
            )

        if moved:
            facts.append(
                IntelligenceFact(
                    source="Whale Intelligence",
                    title="Whale Transfer Movement",
                    description=(
                        f"{moved} whale player(s) changed server or alliance."
                    ),
                    severity=self._severity_from_count(moved),
                    confidence=self._average_confidence(events),
                    evidence=[
                        self._format_event(event)
                        for event in events
                        if event.event == "Moved"
                    ],
                    entity_type=FactEntityType.PLAYER,
                    entity_id="multiple" if moved > 1 else self._single_entity_id(events, "Moved"),
                    tags=["whale", "movement", "transfer"],
                )
            )

        return facts

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

    @staticmethod
    def _severity_from_count(
        count: int,
    ) -> FactSeverity:

        if count >= 3:
            return FactSeverity.CRITICAL

        if count == 2:
            return FactSeverity.HIGH

        return FactSeverity.MEDIUM

    @staticmethod
    def _average_confidence(
        events: list[WhaleEvent],
    ) -> float:

        if not events:
            return 0.0

        return round(
            sum(event.confidence for event in events)
            / len(events),
            2,
        )

    @staticmethod
    def _single_entity_id(
        events: list[WhaleEvent],
        event_type: str,
    ) -> str:

        matching = [
            event
            for event in events
            if event.event == event_type
        ]

        if not matching:
            return ""

        return matching[0].identifier

    @staticmethod
    def _format_event(
        event: WhaleEvent,
    ) -> str:

        name = event.payload.get(
            "name",
            event.identifier,
        )

        if event.event == "Moved":
            changes = event.payload.get(
                "changes",
                {},
            )

            server_change = changes.get("server")
            alliance_change = changes.get("alliance")

            details: list[str] = []

            if server_change:
                details.append(
                    f"server {server_change[0]} → {server_change[1]}"
                )

            if alliance_change:
                details.append(
                    f"alliance {alliance_change[0]} → {alliance_change[1]}"
                )

            movement = ", ".join(details)

            return f"{name} moved ({movement}), power {event.power}M."

        return f"{name} detected as {event.event.lower()} whale, power {event.power}M."