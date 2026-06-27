"""
Sentinel
Watchlist Repository
"""

from __future__ import annotations

from application.watchlist.models import (
    WatchEntityType,
    WatchPriority,
    WatchTarget,
    Watchlist,
)


class WatchlistRepository:
    """
    In-memory repository for watch targets.
    """

    def __init__(self) -> None:
        self._targets: list[WatchTarget] = []

    def add(
        self,
        target: WatchTarget,
    ) -> None:
        if self._exists(target):
            return

        self._targets.append(target)

    def extend(
        self,
        targets: list[WatchTarget],
    ) -> None:
        for target in targets:
            self.add(target)

    def all(
        self,
    ) -> Watchlist:
        return Watchlist(
            targets=list(self._targets),
        )

    def by_priority(
        self,
        priority: WatchPriority,
    ) -> list[WatchTarget]:
        return [
            target
            for target in self._targets
            if target.priority == priority
        ]

    def by_entity_type(
        self,
        entity_type: WatchEntityType,
    ) -> list[WatchTarget]:
        return [
            target
            for target in self._targets
            if target.entity_type == entity_type
        ]

    def by_server(
        self,
        server: int,
    ) -> list[WatchTarget]:
        return [
            target
            for target in self._targets
            if target.server == server
        ]

    def top(
        self,
        limit: int = 10,
    ) -> list[WatchTarget]:
        return sorted(
            self._targets,
            key=lambda target: (
                self._priority_value(target.priority),
                target.score,
            ),
            reverse=True,
        )[:limit]

    def clear(
        self,
    ) -> None:
        self._targets.clear()

    def count(
        self,
    ) -> int:
        return len(self._targets)

    def _exists(
        self,
        target: WatchTarget,
    ) -> bool:
        return any(
            existing.entity_type == target.entity_type
            and existing.server == target.server
            and existing.name.casefold() == target.name.casefold()
            and existing.alliance == target.alliance
            for existing in self._targets
        )

    @staticmethod
    def _priority_value(
        priority: WatchPriority,
    ) -> int:
        mapping = {
            WatchPriority.IMMEDIATE: 5,
            WatchPriority.HIGH: 4,
            WatchPriority.MEDIUM: 3,
            WatchPriority.LOW: 2,
            WatchPriority.ARCHIVE: 1,
        }

        return mapping[priority]