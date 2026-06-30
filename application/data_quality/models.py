"""Data Quality view models for Sentinel operational readiness."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class QualitySummary:
    ground_truth_rows: int = 0
    ocr_rows: int = 0
    matched_rows: int = 0
    missing_rows: int = 0
    bad_matches: int = 0
    gap_blocks: int = 0
    gap_rows: int = 0
    unresolved_gap_rows: int = 0
    blocked_rank_fallbacks: int = 0
    gap_resolved_rows: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    score: float = 0.0
    usable_identity_matches: int = 0
    power_matches: int = 0
    alliance_matches: int = 0
    name_normalized_matches: int = 0


@dataclass(slots=True, frozen=True)
class ReviewItem:
    server: int
    rank: int | None
    title: str
    description: str
    severity: str
    action: str
    reason: str = ""
    screenshot: str = ""


@dataclass(slots=True, frozen=True)
class ServerQuality:
    server: int
    ranking_type: str
    expected_rows: int
    ocr_rows: int
    matched_rows: int
    readiness: int
    status: str
    missing_ranks: list[int] = field(default_factory=list)
    blocked_ranks: list[int] = field(default_factory=list)
    unresolved_ranks: list[int] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class ImportRun:
    source: str
    ranking_type: str
    server: int | None
    rows: int
    status: str
    confidence: int
    detail: str


@dataclass(slots=True, frozen=True)
class QualityDashboard:
    has_report: bool
    report_path: str
    summary: QualitySummary
    servers: list[ServerQuality]
    reviews: list[ReviewItem]
    imports: list[ImportRun]
    recent_operations: list[dict[str, Any]]
