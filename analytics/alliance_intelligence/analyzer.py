"""
Sentinel
Alliance Intelligence Analyzer
"""

from __future__ import annotations

from analytics.alliance_intelligence.models import (
    AllianceAssessment,
    AllianceEvent,
)
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


class AllianceIntelligenceAnalyzer:
    """
    Produces alliance intelligence facts from generic differences.
    """

    POWER_DROP_HIGH = 0.12
    POWER_DROP_CRITICAL = 0.20

    def analyze(
        self,
        differences: DifferenceSet,
    ) -> AllianceAssessment:
        events: list[AllianceEvent] = []

        added = 0
        removed = 0
        moved = 0
        modified = 0

        for difference in differences.by_entity(EntityType.ALLIANCE):
            if difference.difference_type == DifferenceType.ADDED:
                added += 1
                events.append(
                    self._event(
                        difference=difference,
                        event="Added",
                    )
                )

            elif difference.difference_type == DifferenceType.REMOVED:
                removed += 1
                events.append(
                    self._event(
                        difference=difference,
                        event="Removed",
                    )
                )

            elif difference.difference_type == DifferenceType.MOVED:
                moved += 1
                events.append(
                    self._event(
                        difference=difference,
                        event="Moved",
                    )
                )

            elif difference.difference_type == DifferenceType.MODIFIED:
                modified += 1
                events.append(
                    self._event(
                        difference=difference,
                        event="Modified",
                    )
                )

        facts = self._build_facts(
            added=added,
            removed=removed,
            moved=moved,
            modified=modified,
            events=events,
        )

        facts.extend(
            self._build_power_change_facts(
                differences=differences,
            )
        )

        return AllianceAssessment(
            events=events,
            facts=facts,
            added=added,
            removed=removed,
            moved=moved,
            modified=modified,
        )

    def _build_facts(
        self,
        added: int,
        removed: int,
        moved: int,
        modified: int,
        events: list[AllianceEvent],
    ) -> list[IntelligenceFact]:
        facts: list[IntelligenceFact] = []

        if added:
            facts.append(
                IntelligenceFact(
                    source="Alliance Intelligence",
                    title="Alliance Appeared",
                    description=f"{added} alliance(s) appeared in the current snapshot.",
                    severity=self._severity_from_count(added),
                    confidence=self._average_confidence(events),
                    evidence=[
                        self._format_event(event)
                        for event in events
                        if event.event == "Added"
                    ],
                    entity_type=FactEntityType.ALLIANCE,
                    entity_id="multiple" if added > 1 else self._single_entity_id(events, "Added"),
                    tags=["alliance", "appeared"],
                )
            )

        if removed:
            facts.append(
                IntelligenceFact(
                    source="Alliance Intelligence",
                    title="Alliance Disappeared",
                    description=f"{removed} alliance(s) disappeared from the current snapshot.",
                    severity=self._severity_from_count(removed),
                    confidence=self._average_confidence(events),
                    evidence=[
                        self._format_event(event)
                        for event in events
                        if event.event == "Removed"
                    ],
                    entity_type=FactEntityType.ALLIANCE,
                    entity_id="multiple" if removed > 1 else self._single_entity_id(events, "Removed"),
                    tags=["alliance", "disappeared"],
                )
            )

        if moved:
            facts.append(
                IntelligenceFact(
                    source="Alliance Intelligence",
                    title="Alliance Movement",
                    description=f"{moved} alliance(s) changed server or organizational context.",
                    severity=self._severity_from_count(moved),
                    confidence=self._average_confidence(events),
                    evidence=[
                        self._format_event(event)
                        for event in events
                        if event.event == "Moved"
                    ],
                    entity_type=FactEntityType.ALLIANCE,
                    entity_id="multiple" if moved > 1 else self._single_entity_id(events, "Moved"),
                    tags=["alliance", "movement"],
                )
            )

        if modified:
            facts.append(
                IntelligenceFact(
                    source="Alliance Intelligence",
                    title="Alliance Changed",
                    description=f"{modified} alliance(s) changed relevant properties.",
                    severity=FactSeverity.LOW,
                    confidence=self._average_confidence(events),
                    evidence=[
                        self._format_event(event)
                        for event in events
                        if event.event == "Modified"
                    ],
                    entity_type=FactEntityType.ALLIANCE,
                    entity_id="multiple" if modified > 1 else self._single_entity_id(events, "Modified"),
                    tags=["alliance", "changed"],
                )
            )

        return facts

    def _build_power_change_facts(
        self,
        differences: DifferenceSet,
    ) -> list[IntelligenceFact]:
        facts: list[IntelligenceFact] = []

        for difference in differences.by_entity(EntityType.ALLIANCE):
            changes = difference.payload.get(
                "changes",
                {},
            )

            if "power" not in changes:
                continue

            before, after = changes["power"]

            if before in (None, 0) or after is None:
                continue

            delta = (after - before) / before

            if delta >= 0:
                continue

            severity = self._severity_from_power_drop(
                abs(delta)
            )

            if severity is None:
                continue

            name = self._name_from_difference(
                difference
            )

            facts.append(
                IntelligenceFact(
                    source="Alliance Intelligence",
                    title="Alliance Power Drop",
                    description=(
                        f"{name} lost {abs(delta) * 100:.1f}% power "
                        "between snapshots."
                    ),
                    severity=severity,
                    confidence=difference.confidence,
                    evidence=[
                        f"{name}: {before}M → {after}M",
                    ],
                    entity_type=FactEntityType.ALLIANCE,
                    entity_id=difference.identifier,
                    tags=["alliance", "power", "drop"],
                )
            )

        return facts

    def _event(
        self,
        difference: Difference,
        event: str,
    ) -> AllianceEvent:
        return AllianceEvent(
            identifier=difference.identifier,
            event=event,
            confidence=difference.confidence,
            payload=difference.payload,
        )

    def _severity_from_power_drop(
        self,
        drop: float,
    ) -> FactSeverity | None:
        if drop >= self.POWER_DROP_CRITICAL:
            return FactSeverity.CRITICAL

        if drop >= self.POWER_DROP_HIGH:
            return FactSeverity.HIGH

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
        events: list[AllianceEvent],
    ) -> float:
        if not events:
            return 0.0

        return round(
            sum(event.confidence for event in events) / len(events),
            2,
        )

    @staticmethod
    def _single_entity_id(
        events: list[AllianceEvent],
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
        event: AllianceEvent,
    ) -> str:
        name = event.payload.get(
            "name",
            event.identifier,
        )

        return f"{name} detected as {event.event.lower()} alliance."

    @staticmethod
    def _name_from_difference(
        difference: Difference,
    ) -> str:
        if "name" in difference.payload:
            return str(difference.payload["name"])

        return difference.identifier