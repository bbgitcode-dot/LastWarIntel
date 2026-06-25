"""
LastWarIntel
Assessment Converter
Version: 1.0

Converters from legacy/domain-specific assessment objects into the universal
Assessment model.
"""

from __future__ import annotations

from analytics.assessment.models import Assessment, AssessmentType, Evidence
from analytics.events.models import EntityType, EventType


class AllianceHealthAssessmentConverter:
    """
    Converts AllianceHealth objects into universal Assessment objects.
    """

    def convert(self, health) -> Assessment:
        evidence = self._build_evidence(health)

        return Assessment(
            assessment_type=AssessmentType.ALLIANCE_HEALTH,
            entity_type=EntityType.ALLIANCE,
            entity=health.alliance,
            score=health.score,
            confidence=self._confidence(health, evidence),
            summary=self._summary(health),
            evidence=evidence,
            metadata={
                "server": health.server,
                "status": health.status,
                "trend": health.trend,
                "risk": health.risk,
                "facts": health.facts,
            },
        )

    def convert_many(self, health_items: list) -> list[Assessment]:
        return [self.convert(item) for item in health_items]

    def _build_evidence(self, health) -> list[Evidence]:
        evidence: list[Evidence] = []

        for event in health.events:
            evidence.append(self._evidence_from_event(event))

        for reason in health.reasons:
            evidence.append(
                Evidence(
                    source="HealthReason",
                    title="Health reason",
                    explanation=reason,
                    weight=self._reason_weight(reason),
                    confidence=80.0,
                    metadata={
                        "server": health.server,
                        "alliance": health.alliance,
                    },
                )
            )

        return evidence

    def _evidence_from_event(self, event) -> Evidence:
        return Evidence(
            source="Event",
            title=event.event_type.value,
            explanation=event.summary,
            weight=self._event_weight(event),
            confidence=event.confidence * 100,
            metadata={
                "server": event.server,
                "entity": event.entity,
                "event_type": event.event_type.value,
                "severity": event.severity.name,
                "facts": event.facts,
                "evidence": event.evidence,
            },
        )

    @staticmethod
    def _event_weight(event) -> float:
        if event.event_type == EventType.LEFT_TOP10:
            return 45.0

        if event.event_type == EventType.ENTERED_TOP10:
            return 18.0

        if event.event_type == EventType.POWER_CHANGED:
            percent = event.facts.get("percent", 0)

            if percent <= -25:
                return 30.0
            if percent <= -10:
                return 18.0
            if percent >= 25:
                return 20.0
            if percent >= 10:
                return 10.0

            return 5.0

        if event.event_type == EventType.RANK_CHANGED:
            delta = event.facts.get("rank_delta", 0)

            if delta <= -3:
                return 12.0
            if delta >= 3:
                return 8.0

            return 4.0

        return 5.0

    @staticmethod
    def _reason_weight(reason: str) -> float:
        lowered = reason.lower()

        if "left the latest top10" in lowered:
            return 45.0

        if "missing from the latest" in lowered:
            return 20.0

        if "severe power loss" in lowered:
            return 30.0

        if "power loss" in lowered:
            return 18.0

        if "strong power growth" in lowered:
            return 20.0

        if "moderate power growth" in lowered:
            return 10.0

        if "dropped" in lowered:
            return 12.0

        if "climbed" in lowered:
            return 8.0

        return 3.0

    @staticmethod
    def _confidence(health, evidence: list[Evidence]) -> float:
        if not evidence:
            return 50.0

        evidence_score = min(len(evidence) * 12, 60)
        event_score = min(len(health.events) * 10, 30)
        fact_score = 10 if health.facts else 0

        return round(min(100.0, evidence_score + event_score + fact_score), 2)

    @staticmethod
    def _summary(health) -> str:
        return (
            f"{health.alliance} health is {health.status} "
            f"with {health.trend} trend and {health.risk} risk."
        )