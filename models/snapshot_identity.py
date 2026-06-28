"""Snapshot identity models for historically traceable imports.

A SnapshotKey identifies the logical observation represented by a snapshot.
It deliberately excludes repository revision information: repeated imports of
identical logical data can be skipped, replaced, or stored as a new revision.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional


@dataclass(frozen=True, slots=True)
class SnapshotKey:
    """Stable identity for one logical ranking snapshot."""

    season: str
    server: int
    ranking_type: str
    captured_date: date

    @classmethod
    def from_datetime(
        cls,
        *,
        season: str,
        server: int,
        ranking_type: str,
        captured_at: Optional[datetime] = None,
    ) -> "SnapshotKey":
        if captured_at is None:
            captured_at = datetime.now(timezone.utc)
        if captured_at.tzinfo is None:
            captured_at = captured_at.replace(tzinfo=timezone.utc)
        return cls(
            season=str(season),
            server=int(server),
            ranking_type=str(ranking_type),
            captured_date=captured_at.date(),
        )

    @property
    def canonical_id(self) -> str:
        """Return a deterministic filesystem-safe ID."""
        return (
            f"{self.season}__s{self.server}__{self.ranking_type}__"
            f"{self.captured_date.isoformat()}"
        )


@dataclass(frozen=True, slots=True)
class SnapshotRecord:
    """Repository metadata for a stored snapshot."""

    key: SnapshotKey
    snapshot_id: str
    revision: int
    created_at: datetime
    source_file: Optional[str] = None

    @property
    def canonical_id(self) -> str:
        return self.key.canonical_id


@dataclass(frozen=True, slots=True)
class SnapshotSaveResult:
    """Result of a repository save operation."""

    action: str
    record: SnapshotRecord
    path: str
