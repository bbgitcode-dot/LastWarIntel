"""View models for managed Sentinel snapshots.

A managed snapshot is a human-named import context such as "S6 pre Transfer".
It is deliberately separate from the low-level SQLite `snapshots` table, which
stores server-specific ranking records.  The managed snapshot tells reviewers
and importers *why* a batch exists and which phase it belongs to.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class ServerScope:
    mode: str = "selected"
    start: int | None = None
    end: int | None = None
    servers: list[int] = field(default_factory=list)

    @property
    def label(self) -> str:
        if self.mode == "all":
            return "All known servers"
        if self.mode == "range" and self.start and self.end:
            return f"{self.start}-{self.end}"
        if self.servers:
            return ", ".join(str(server) for server in self.servers)
        return "not fixed yet"


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
    server_scope: ServerScope = field(default_factory=ServerScope)
    locked: bool = False
    audit: list[SnapshotAuditEntry] = field(default_factory=list)
    completion_report_file: str = ""


@dataclass(slots=True, frozen=True)
class SnapshotFeedCoverage:
    server: int | None
    ranking_type: str
    rows: int
    screenshots: int
    status: str
    source: str = ""


@dataclass(slots=True, frozen=True)
class SnapshotMissingFeed:
    server: int | None
    ranking_type: str
    reason: str


@dataclass(slots=True, frozen=True)
class SnapshotCoverage:
    snapshot: ManagedSnapshot | None
    is_bound: bool
    bound_snapshot_id: str
    bound_snapshot_name: str
    report_created_at: str
    expected_rankings: list[str]
    expected_servers: list[int]
    expected_feed_count: int
    imported_valid_feed_count: int
    completeness_percent: float
    imported_servers: list[int]
    imported_rankings: list[str]
    imported_feeds: list[SnapshotFeedCoverage]
    missing_feeds: list[SnapshotMissingFeed]
    open_review_count: int
    output_file: str
    warning: str = ""


@dataclass(slots=True, frozen=True)
class SnapshotReadiness:
    status: str
    operational_truth_ready: bool
    expected_feeds_ok: bool
    completeness_ok: bool
    reviews_ok: bool
    data_guard_ok: bool
    ranking_guard_ok: bool
    locked: bool
    missing_feed_count: int
    open_review_count: int
    validated_feed_count: int
    expected_feed_count: int
    completeness_percent: float
    message: str


@dataclass(slots=True, frozen=True)
class SnapshotAuditEntry:
    event: str
    at: str
    actor: str = "sentinel"
    detail: str = ""


@dataclass(slots=True, frozen=True)
class SnapshotDashboard:
    has_active: bool
    active: ManagedSnapshot | None
    snapshots: list[ManagedSnapshot]
    open_count: int
    total_count: int
    storage_path: str
    active_coverage: SnapshotCoverage | None = None
    active_readiness: SnapshotReadiness | None = None
