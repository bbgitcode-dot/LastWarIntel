"""
Sentinel
Comparison Models
"""

from __future__ import annotations

from dataclasses import dataclass, field

from analytics.comparison.difference import (
    Difference,
    DifferenceType,
    EntityType,
)


@dataclass(slots=True, frozen=True)
class ComparisonStatistics:
    """
    High-level statistics describing a comparison.
    """

    duration_hours: float

    alliance_changes: int

    player_changes: int

    power_delta: float

    snapshots_compared: int = 2


@dataclass(slots=True, frozen=True)
class DifferenceSet:
    """
    Generic collection of detected differences.

    All intelligence modules should consume this model
    instead of maintaining separate added / removed /
    changed lists.
    """

    differences: list[Difference] = field(default_factory=list)

    def __iter__(self):
        return iter(self.differences)

    def __len__(self) -> int:
        return len(self.differences)

    def by_entity(
        self,
        entity_type: EntityType,
    ) -> list[Difference]:
        return [
            difference
            for difference in self.differences
            if difference.entity_type == entity_type
        ]

    def by_type(
        self,
        difference_type: DifferenceType,
    ) -> list[Difference]:
        return [
            difference
            for difference in self.differences
            if difference.difference_type == difference_type
        ]

    @property
    def added(self) -> list[Difference]:
        return self.by_type(DifferenceType.ADDED)

    @property
    def removed(self) -> list[Difference]:
        return self.by_type(DifferenceType.REMOVED)

    @property
    def changed(self) -> list[Difference]:
        return self.by_type(DifferenceType.MODIFIED)

    @property
    def moved(self) -> list[Difference]:
        return self.by_type(DifferenceType.MOVED)