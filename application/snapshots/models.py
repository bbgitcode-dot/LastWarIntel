"""View models for managed Sentinel snapshots.

A managed snapshot is a human-named import context such as "S6 pre Transfer".
It is deliberately separate from the low-level SQLite `snapshots` table, which
stores server-specific ranking records.  The managed snapshot tells reviewers
and importers *why* a batch exists and which phase it belongs to.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class ManagedSnapshot:
    id: str
    name: str
    snapshot_type: str
    status: str
    description: str
    expected_rankings: list[str]
    created_at: str
    updated_at: str
    source: str = ""
    assigned_servers: list[int] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class SnapshotDashboard:
    has_active: bool
    active: ManagedSnapshot | None
    snapshots: list[ManagedSnapshot]
    open_count: int
    total_count: int
    storage_path: str
