"""View models for the Sentinel Command Center."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class StatusBadge:
    label: str
    tone: str
    detail: str


@dataclass(slots=True, frozen=True)
class MissionViewModel:
    title: str
    description: str
    action: str
    tone: str
    effort: str


@dataclass(slots=True, frozen=True)
class AttentionItem:
    title: str
    description: str
    severity: str
    action: str


@dataclass(slots=True, frozen=True)
class OperationalMetric:
    title: str
    value: str
    subtitle: str
    tone: str


@dataclass(slots=True, frozen=True)
class SystemComponent:
    name: str
    status: str
    detail: str
    tone: str


@dataclass(slots=True, frozen=True)
class OperationalStatusCard:
    title: str
    value: str
    subtitle: str
    tone: str
    href: str
    description: str


@dataclass(slots=True, frozen=True)
class ServerHealthItem:
    server: int
    status: str
    tone: str
    href: str
    detail: str


@dataclass(slots=True, frozen=True)
class OperationalReadiness:
    total_servers: int
    operational_servers: int
    pending_review_servers: int
    missing_data_servers: int
    failed_import_servers: int
    coverage_percent: int
    cards: list[OperationalStatusCard]
    server_health: list[ServerHealthItem]




@dataclass(slots=True, frozen=True)
class ActiveSnapshotView:
    name: str
    snapshot_type: str
    status: str
    expected_rankings: list[str]
    storage_path: str


@dataclass(slots=True, frozen=True)
class ActivityItem:
    time: str
    title: str
    detail: str
    severity: str


@dataclass(slots=True, frozen=True)
class CommandCenterViewModel:
    title: str
    subtitle: str
    version: str
    status: StatusBadge
    readiness: int
    mission: MissionViewModel
    attention_items: list[AttentionItem]
    operational_readiness: OperationalReadiness
    active_snapshot: ActiveSnapshotView | None
    metrics: list[OperationalMetric]
    components: list[SystemComponent]
    activity: list[ActivityItem]
