"""Structured player ranking models for OCR-derived THP snapshots.

These models represent parsed ranking data after OCR extraction but before
matching, difference detection, or intelligence generation. They are deliberately
small and deterministic so downstream layers can depend on structured data
instead of raw OCR strings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from models.snapshot_identity import SnapshotKey


@dataclass(slots=True)
class PlayerRankingEntry:
    """One structured Total Hero Power ranking row."""

    rank: int
    server: int
    alliance_tag: Optional[str]
    player_name: str
    hero_power: int
    ocr_rank: Optional[int] = None
    computed_rank: Optional[int] = None
    rank_warning: Optional[str] = None
    server_confidence: Optional[float] = None
    server_source: Optional[str] = None
    server_warning: Optional[str] = None
    data_guard_conflict: bool = False
    snapshot_id: Optional[str] = None
    confidence: float = 1.0
    source_file: Optional[str] = None
    raw_text: Optional[str] = None
    parse_status: str = "VALID"
    parse_warnings: list[str] = field(default_factory=list)
    parse_corrections: list[str] = field(default_factory=list)
    normalized_identity: Optional[str] = None
    identity_fidelity_status: str = "PASS"
    identity_fidelity_risk: str = "low"
    identity_fidelity_warnings: list[str] = field(default_factory=list)
    case_sensitive_alliance_tag: Optional[str] = None
    canonical_alliance_tag: Optional[str] = None
    visual_y: Optional[float] = None

    def to_legacy_row(self) -> dict:
        """Return a dict compatible with the current merge/export pipeline."""
        display_name = self.player_name
        if self.alliance_tag:
            display_name = f"[{self.alliance_tag}] {self.player_name}".strip()

        return {
            "rank": self.rank,
            "server": self.server,
            "alliance_tag": self.alliance_tag,
            "player_name": self.player_name,
            "name": display_name,
            "power": self.hero_power,
            "hero_power": self.hero_power,
            "ocr_rank": self.ocr_rank,
            "computed_rank": self.computed_rank,
            "rank_warning": self.rank_warning,
            "server_confidence": self.server_confidence,
            "server_source": self.server_source,
            "server_warning": self.server_warning,
            "data_guard_conflict": self.data_guard_conflict,
            "snapshot_id": self.snapshot_id,
            "confidence": self.confidence,
            "source_file": self.source_file,
            "raw_text": self.raw_text,
            "parse_status": self.parse_status,
            "parse_warnings": ";".join(self.parse_warnings),
            "parse_corrections": ";".join(self.parse_corrections),
            "normalized_identity": self.normalized_identity,
            "identity_fidelity_status": self.identity_fidelity_status,
            "identity_fidelity_risk": self.identity_fidelity_risk,
            "identity_fidelity_warnings": ";".join(self.identity_fidelity_warnings),
            "case_sensitive_alliance_tag": self.case_sensitive_alliance_tag,
            "canonical_alliance_tag": self.canonical_alliance_tag,
            "visual_y": self.visual_y,
        }


@dataclass(slots=True)
class PlayerRankingSnapshot:
    """Structured Total Hero Power snapshot for one server/import source."""

    server: int
    ranking_type: str
    entries: list[PlayerRankingEntry] = field(default_factory=list)
    snapshot_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_file: Optional[str] = None
    season: str = "unknown"

    def key(self) -> SnapshotKey:
        """Return the stable logical identity for this snapshot."""
        return SnapshotKey.from_datetime(
            season=self.season,
            server=self.server,
            ranking_type=self.ranking_type,
            captured_at=self.created_at,
        )

    def with_identity(self, season: str, snapshot_id: Optional[str] = None) -> "PlayerRankingSnapshot":
        """Assign season and snapshot_id while preserving parsed entries."""
        self.season = season
        if snapshot_id is not None:
            self.snapshot_id = snapshot_id
            for entry in self.entries:
                entry.snapshot_id = snapshot_id
        return self

    def to_legacy_rows(self) -> list[dict]:
        return [entry.to_legacy_row() for entry in self.entries]
