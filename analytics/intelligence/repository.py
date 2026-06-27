"""
Sentinel
Intelligence Repository
"""

from __future__ import annotations

from collections import defaultdict

from analytics.reasoning.models import (
    FactEntityType,
    FactSeverity,
    IntelligenceFact,
)


class IntelligenceRepository:
    """
    In-memory repository for intelligence facts.

    This repository represents the central knowledge store
    of the current Sentinel session.

    All intelligence modules publish facts here.
    Other modules consume facts from here.
    """

    def __init__(self) -> None:

        self._facts: list[IntelligenceFact] = []

    #
    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    #

    def add(
        self,
        fact: IntelligenceFact,
    ) -> None:

        self._facts.append(fact)

    def extend(
        self,
        facts: list[IntelligenceFact],
    ) -> None:

        self._facts.extend(facts)

    def clear(self) -> None:

        self._facts.clear()

    #
    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------
    #

    def all(
        self,
    ) -> list[IntelligenceFact]:

        return list(self._facts)

    def latest(
        self,
        limit: int = 25,
    ) -> list[IntelligenceFact]:

        return sorted(
            self._facts,
            key=lambda fact: fact.timestamp,
            reverse=True,
        )[:limit]

    def by_source(
        self,
        source: str,
    ) -> list[IntelligenceFact]:

        normalized = source.casefold()

        return [
            fact
            for fact in self._facts
            if fact.source.casefold() == normalized
        ]

    def by_tag(
        self,
        tag: str,
    ) -> list[IntelligenceFact]:

        normalized = tag.casefold()

        return [
            fact
            for fact in self._facts
            if any(
                t.casefold() == normalized
                for t in fact.tags
            )
        ]

    def by_entity(
        self,
        entity_type: FactEntityType,
        entity_id: str,
    ) -> list[IntelligenceFact]:

        return [
            fact
            for fact in self._facts
            if (
                fact.entity_type == entity_type
                and fact.entity_id == entity_id
            )
        ]

    def by_severity(
        self,
        severity: FactSeverity,
    ) -> list[IntelligenceFact]:

        return [
            fact
            for fact in self._facts
            if fact.severity == severity
        ]

    #
    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------
    #

    def count(self) -> int:

        return len(self._facts)

    def count_by_source(
        self,
    ) -> dict[str, int]:

        counts: dict[str, int] = defaultdict(int)

        for fact in self._facts:
            counts[fact.source] += 1

        return dict(counts)

    def count_by_tag(
        self,
    ) -> dict[str, int]:

        counts: dict[str, int] = defaultdict(int)

        for fact in self._facts:
            for tag in fact.tags:
                counts[tag] += 1

        return dict(counts)

    def count_by_entity_type(
        self,
    ) -> dict[str, int]:

        counts: dict[str, int] = defaultdict(int)

        for fact in self._facts:
            counts[fact.entity_type.value] += 1

        return dict(counts)

    #
    # ------------------------------------------------------------------
    # Breaking News
    # ------------------------------------------------------------------
    #

    def breaking_news(
        self,
        limit: int = 20,
    ) -> list[IntelligenceFact]:

        severity_order = {
            FactSeverity.CRITICAL: 4,
            FactSeverity.HIGH: 3,
            FactSeverity.MEDIUM: 2,
            FactSeverity.LOW: 1,
        }

        return sorted(
            self._facts,
            key=lambda fact: (
                severity_order[fact.severity],
                fact.confidence,
                fact.timestamp,
            ),
            reverse=True,
        )[:limit]