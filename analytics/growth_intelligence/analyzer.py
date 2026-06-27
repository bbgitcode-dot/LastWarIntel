"""
Sentinel
Growth Intelligence Analyzer
"""

from __future__ import annotations

from analytics.comparison.difference import (
    Difference,
    EntityType,
)
from analytics.comparison.models import DifferenceSet
from analytics.growth_intelligence.models import (
    GrowthAssessment,
    GrowthEvent,
)
from analytics.reasoning.models import (
    FactEntityType,
    FactSeverity,
    IntelligenceFact,
)


class GrowthIntelligenceAnalyzer:
    """
    Produces growth intelligence facts from generic differences.
    """

    GROWTH_MEDIUM = 0.08
    GROWTH_HIGH = 0.15
    GROWTH_CRITICAL = 0.25

    DECLINE_MEDIUM = 0.08
    DECLINE_HIGH = 0.15
    DECLINE_CRITICAL = 0.25

    def analyze(
        self,
        differences: DifferenceSet,
    ) -> GrowthAssessment:
        events: list[GrowthEvent] = []

        for difference in differences:
            if difference.entity_type not in (
                EntityType.ALLIANCE,
                EntityType.PLAYER,
                EntityType.SERVER,
            ):
                continue

            changes = difference.payload.get(
                "changes",
                {},
            )

            if "power" not in changes:
                continue

            before, after = changes["power"]

            if before in (None, 0) or after is None:
                continue

            change_percent = (after - before) / before

            if abs(change_percent) < self.GROWTH_MEDIUM:
                continue

            event = "Growth" if change_percent > 0 else "Decline"

            events.append(
                GrowthEvent(
                    identifier=difference.identifier,
                    event=event,
                    change_percent=change_percent,
                    confidence=difference.confidence,
                    payload=difference.payload,
                )
            )

        facts = self._build_facts(
            events,
        )

        return GrowthAssessment(
            events=events,
            facts=facts,
            growth=sum(1 for event in events if event.event == "Growth"),
            decline=sum(1 for event in events if event.event == "Decline"),
        )

    def _build_facts(
        self,
        events: list[GrowthEvent],
    ) -> list[IntelligenceFact]:
        facts: list[IntelligenceFact] = []

        for event in events:
            severity = self._severity_from_change(
                event.change_percent,
            )

            entity_type = self._fact_entity_type(
                event,
            )

            name = self._name_from_event(
                event,
            )

            direction = "gained" if event.change_percent > 0 else "lost"

            facts.append(
                IntelligenceFact(
                    source="Growth Intelligence",
                    title=f"{entity_type.value} {event.event}",
                    description=(
                        f"{name} {direction} "
                        f"{abs(event.change_percent) * 100:.1f}% power "
                        "between snapshots."
                    ),
                    severity=severity,
                    confidence=event.confidence,
                    evidence=[
                        self._format_evidence(event),
                    ],
                    entity_type=entity_type,
                    entity_id=event.identifier,
                    tags=[
                        "growth",
                        event.event.casefold(),
                        entity_type.value.casefold(),
                    ],
                )
            )

        return facts

    def _severity_from_change(
        self,
        change_percent: float,
    ) -> FactSeverity:
        absolute = abs(change_percent)

        if absolute >= self.GROWTH_CRITICAL:
            return FactSeverity.CRITICAL

        if absolute >= self.GROWTH_HIGH:
            return FactSeverity.HIGH

        return FactSeverity.MEDIUM

    @staticmethod
    def _fact_entity_type(
        event: GrowthEvent,
    ) -> FactEntityType:
        entity_type = event.payload.get(
            "entity_type",
            "",
        )

        if entity_type == EntityType.PLAYER.value:
            return FactEntityType.PLAYER

        if entity_type == EntityType.SERVER.value:
            return FactEntityType.SERVER

        return FactEntityType.ALLIANCE

    @staticmethod
    def _name_from_event(
        event: GrowthEvent,
    ) -> str:
        return str(
            event.payload.get(
                "name",
                event.identifier,
            )
        )

    @staticmethod
    def _format_evidence(
        event: GrowthEvent,
    ) -> str:
        changes = event.payload.get(
            "changes",
            {},
        )

        before, after = changes["power"]

        name = event.payload.get(
            "name",
            event.identifier,
        )

        return f"{name}: {before}M → {after}M"