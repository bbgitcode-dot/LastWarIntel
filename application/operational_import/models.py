"""Operational import view models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class ServerImportView:
    source: str
    server: int | None
    ranking_type: str
    rows: int
    status: str
    confidence: int
    review_count: int
    screenshots: int


@dataclass(slots=True, frozen=True)
class ImportReviewView:
    title: str
    description: str
    severity: str
    action: str
    reason: str
    server: int | None = None
    rank: int | None = None
    screenshot: str = ""


@dataclass(slots=True, frozen=True)
class DataGuardStatusView:
    status: str
    warnings: int
    critical: int
    checks: list[str] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class OperationalImportDashboard:
    has_import: bool
    source: str
    created_at: str = ""
    runtime_seconds: float = 0.0
    screenshots: int = 0
    server_count: int = 0
    rows: int = 0
    status: str = "Pending"
    readiness: int = 0
    review_count: int = 0
    output_file: str = ""
    servers: list[int] = field(default_factory=list)
    imports: list[ServerImportView] = field(default_factory=list)
    reviews: list[ImportReviewView] = field(default_factory=list)
    data_guard: DataGuardStatusView = field(default_factory=lambda: DataGuardStatusView("Pending", 0, 0, []))
    recent_operations: list[dict[str, Any]] = field(default_factory=list)
