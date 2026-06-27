"""
Sentinel
Snapshot Timeline
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True, frozen=True)
class SnapshotReference:

    snapshot_id: str

    timestamp: datetime

    campaign_id: str

    milestone_id: str | None

    description: str = ""


@dataclass(slots=True)
class SnapshotTimeline:

    server: int

    snapshots: list[SnapshotReference] = field(
        default_factory=list
    )

    def latest(self) -> SnapshotReference | None:

        if not self.snapshots:
            return None

        return max(
            self.snapshots,
            key=lambda s: s.timestamp,
        )

    def first(self) -> SnapshotReference | None:

        if not self.snapshots:
            return None

        return min(
            self.snapshots,
            key=lambda s: s.timestamp,
        )