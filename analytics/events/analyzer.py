"""
LastWarIntel
Event Engine
Version: 1.0

Alliance event analyzer.

This module detects meaningful alliance-level changes from historical
Top10 alliance snapshots.
"""

from __future__ import annotations

from typing import Callable

from analytics.events.models import (
    AllianceHistory,
    EntityType,
    Event,
    EventType,
    Severity,
    Snapshot,
)
from services.server_repository import ServerRepository


class AllianceEventAnalyzer:
    """
    Detects alliance-level events for one server.

    The analyzer does not know SQL.
    It only consumes normalized alliance histories from ServerRepository.
    """

    def __init__(self):
        self.repo = ServerRepository()

        self.detectors: list[
            Callable[[int, dict[str, AllianceHistory]], list[Event]]
        ] = [
            self.detect_entered_top10,
            self.detect_left_top10,
            self.detect_rank_changes,
            self.detect_power_changes,
        ]

    def analyze(self, server: int) -> list[Event]:
        """
        Analyze one server and return all detected alliance events.
        """

        histories = self.load_histories(server)

        events: list[Event] = []

        for detector in self.detectors:
            events.extend(detector(server, histories))

        return sorted(
            events,
            key=lambda event: (
                -event.severity.value,
                event.entity,
                event.event_type.value,
            ),
        )

    def load_histories(self, server: int) -> dict[str, AllianceHistory]:
        """
        Load raw repository rows and convert them into AllianceHistory objects.
        """

        raw_histories = self.repo.get_all_alliance_histories(server)

        histories: dict[str, AllianceHistory] = {}

        for tag, rows in raw_histories.items():
            snapshots: list[Snapshot] = []

            name = tag

            for row in rows:
                name = row["name"] or tag

                snapshots.append(
                    Snapshot(
                        collection=row["collection"],
                        rank=row["rank"],
                        power=row["power"],
                    )
                )

            histories[tag] = AllianceHistory(
                tag=tag,
                name=name,
                snapshots=snapshots,
            )

        return histories

    def detect_entered_top10(
        self,
        server: int,
        histories: dict[str, AllianceHistory],
    ) -> list[Event]:
        """
        Detect alliances that entered the latest Top10 but were not present
        in the earliest available Top10 snapshot.
        """

        events: list[Event] = []

        latest_collection = self._latest_collection(histories)

        if not latest_collection:
            return events

        for alliance in histories.values():
            if len(alliance.snapshots) < 2:
                continue

            first = alliance.first
            last = alliance.last

            if not first or not last:
                continue

            if last.collection != latest_collection:
                continue

            if first.collection == latest_collection:
                events.append(
                    Event(
                        event_type=EventType.ENTERED_TOP10,
                        entity_type=EntityType.ALLIANCE,
                        entity=alliance.tag,
                        server=server,
                        severity=Severity.HIGH
                        if last.rank <= 5
                        else Severity.MEDIUM,
                        confidence=0.95,
                        summary=(
                            f"{alliance.tag} entered the latest Top10 "
                            f"at rank #{last.rank}."
                        ),
                        facts={
                            "new_rank": last.rank,
                            "new_power": last.power,
                            "collection": last.collection,
                        },
                        evidence=[last.collection],
                    )
                )

        return events

    def detect_left_top10(
        self,
        server: int,
        histories: dict[str, AllianceHistory],
    ) -> list[Event]:
        """
        Detect alliances that were present before but are missing from the
        latest Top10 snapshot.
        """

        events: list[Event] = []

        latest_collection = self._latest_collection(histories)

        if not latest_collection:
            return events

        for alliance in histories.values():
            if len(alliance.snapshots) < 1:
                continue

            last = alliance.last

            if not last:
                continue

            if last.collection != latest_collection:
                events.append(
                    Event(
                        event_type=EventType.LEFT_TOP10,
                        entity_type=EntityType.ALLIANCE,
                        entity=alliance.tag,
                        server=server,
                        severity=Severity.HIGH,
                        confidence=0.90,
                        summary=(
                            f"{alliance.tag} left the latest Top10 "
                            f"after last being seen in {last.collection}."
                        ),
                        facts={
                            "last_rank": last.rank,
                            "last_power": last.power,
                            "last_seen": last.collection,
                            "latest_collection": latest_collection,
                        },
                        evidence=[last.collection, latest_collection],
                    )
                )

        return events

    def detect_rank_changes(
        self,
        server: int,
        histories: dict[str, AllianceHistory],
    ) -> list[Event]:
        """
        Detect meaningful rank changes between first and latest appearance.
        """

        events: list[Event] = []

        for alliance in histories.values():
            if len(alliance.snapshots) < 2:
                continue

            first = alliance.first
            last = alliance.last

            if not first or not last:
                continue

            rank_delta = first.rank - last.rank

            if rank_delta == 0:
                continue

            severity = self._rank_change_severity(rank_delta)

            events.append(
                Event(
                    event_type=EventType.RANK_CHANGED,
                    entity_type=EntityType.ALLIANCE,
                    entity=alliance.tag,
                    server=server,
                    severity=severity,
                    confidence=0.95,
                    summary=(
                        f"{alliance.tag} moved from rank #{first.rank} "
                        f"to #{last.rank}."
                    ),
                    facts={
                        "old_rank": first.rank,
                        "new_rank": last.rank,
                        "rank_delta": rank_delta,
                    },
                    evidence=[first.collection, last.collection],
                )
            )

        return events

    def detect_power_changes(
        self,
        server: int,
        histories: dict[str, AllianceHistory],
    ) -> list[Event]:
        """
        Detect meaningful power changes between first and latest appearance.
        """

        events: list[Event] = []

        for alliance in histories.values():
            if len(alliance.snapshots) < 2:
                continue

            first = alliance.first
            last = alliance.last

            if not first or not last:
                continue

            if first.power <= 0:
                continue

            diff = last.power - first.power
            percent = (diff / first.power) * 100

            if abs(percent) < 5:
                continue

            event_type = (
                EventType.POWER_CHANGED
            )

            severity = self._power_change_severity(percent)

            direction = "gained" if diff > 0 else "lost"

            events.append(
                Event(
                    event_type=event_type,
                    entity_type=EntityType.ALLIANCE,
                    entity=alliance.tag,
                    server=server,
                    severity=severity,
                    confidence=0.95,
                    summary=(
                        f"{alliance.tag} {direction} {abs(percent):.2f}% "
                        f"power from {first.collection} to {last.collection}."
                    ),
                    facts={
                        "old_power": first.power,
                        "new_power": last.power,
                        "diff": diff,
                        "percent": percent,
                    },
                    evidence=[first.collection, last.collection],
                )
            )

        return events

    @staticmethod
    def _latest_collection(
        histories: dict[str, AllianceHistory],
    ) -> str | None:
        """
        Determine the latest collection present in the given histories.
        """

        order = {
            "S4 Server Summary": 1,
            "S5 Pre Transfer": 2,
            "S5 Post Transfer": 3,
            "S6 Preseason Alliances": 4,
        }

        collections = {
            snapshot.collection
            for history in histories.values()
            for snapshot in history.snapshots
        }

        if not collections:
            return None

        return max(collections, key=lambda name: order.get(name, 999))

    @staticmethod
    def _rank_change_severity(rank_delta: int) -> Severity:
        """
        Convert rank movement into severity.

        Positive rank_delta means improvement.
        Negative rank_delta means decline.
        """

        absolute = abs(rank_delta)

        if absolute >= 5:
            return Severity.HIGH

        if absolute >= 3:
            return Severity.MEDIUM

        return Severity.LOW

    @staticmethod
    def _power_change_severity(percent: float) -> Severity:
        """
        Convert power change percentage into severity.
        """

        absolute = abs(percent)

        if absolute >= 30:
            return Severity.CRITICAL

        if absolute >= 15:
            return Severity.HIGH

        if absolute >= 8:
            return Severity.MEDIUM

        return Severity.LOW