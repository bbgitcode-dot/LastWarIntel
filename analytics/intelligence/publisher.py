"""
Sentinel
Intelligence Publisher
"""

from __future__ import annotations

from analytics.intelligence.repository import IntelligenceRepository
from analytics.reasoning.models import IntelligenceFact


class IntelligencePublisher:
    """
    Publishes intelligence facts into the repository.

    The publisher is responsible for

    - validation
    - deduplication
    - persistence

    Business logic belongs to the intelligence modules,
    not the publisher.
    """

    def __init__(
        self,
        repository: IntelligenceRepository | None = None,
    ) -> None:

        self._repository = repository or IntelligenceRepository()

    @property
    def repository(
        self,
    ) -> IntelligenceRepository:

        return self._repository

    #
    # ----------------------------------------------------------
    # Publish
    # ----------------------------------------------------------
    #

    def publish(
        self,
        fact: IntelligenceFact,
    ) -> bool:

        if not self._validate(fact):
            return False

        if self._is_duplicate(fact):
            return False

        self._repository.add(fact)

        return True

    def publish_many(
        self,
        facts: list[IntelligenceFact],
    ) -> int:

        published = 0

        for fact in facts:

            if self.publish(fact):
                published += 1

        return published

    #
    # ----------------------------------------------------------
    # Validation
    # ----------------------------------------------------------
    #

    @staticmethod
    def _validate(
        fact: IntelligenceFact,
    ) -> bool:

        return bool(
            fact.title.strip()
            and fact.source.strip()
        )

    #
    # ----------------------------------------------------------
    # Duplicate Detection
    # ----------------------------------------------------------
    #

    def _is_duplicate(
        self,
        fact: IntelligenceFact,
    ) -> bool:

        for existing in self._repository.all():

            if (
                existing.source == fact.source
                and existing.title == fact.title
                and existing.entity_type == fact.entity_type
                and existing.entity_id == fact.entity_id
                and existing.description == fact.description
            ):
                return True

        return False