"""Structured parser for Total Hero Power ranking rows."""

from __future__ import annotations

import re
from typing import Optional

from models.player_ranking import PlayerRankingEntry, PlayerRankingSnapshot
from parser.player_identity_quality import parse_player_identity_quality


def split_alliance_tag_and_player_name_with_confidence(
    raw_name: str,
) -> tuple[Optional[str], str, float]:
    """Split a raw OCR name into normalized alliance tag, name and confidence.

    Backward-compatible public API. For quality details use
    parser.player_identity_quality.parse_player_identity_quality.
    """
    result = parse_player_identity_quality(raw_name)
    return result.alliance_tag, result.player_name, result.confidence

def split_alliance_tag_and_player_name(raw_name: str) -> tuple[Optional[str], str]:
    """Backward-compatible split helper used by existing callers/tests."""
    alliance_tag, player_name, _confidence = split_alliance_tag_and_player_name_with_confidence(raw_name)
    return alliance_tag, player_name


def build_player_ranking_entries(
    rows: list[dict],
    server: int,
    snapshot_id: Optional[str] = None,
    source_file: Optional[str] = None,
    server_confidence: Optional[float] = None,
    server_source: Optional[str] = None,
    server_warning: Optional[str] = None,
) -> list[PlayerRankingEntry]:
    """Convert legacy parsed OCR rows into structured THP entries."""
    entries: list[PlayerRankingEntry] = []

    if server is None:
        raise ValueError("Cannot build player ranking entries without a validated server.")

    sorted_rows = sorted(
        [row for row in rows if row.get("power")],
        key=lambda row: row["power"],
        reverse=True,
    )

    for index, row in enumerate(sorted_rows, start=1):
        row_confidence = row.get("confidence")
        if row_confidence is None:
            row_confidence = 1.0

        identity_quality = parse_player_identity_quality(
            row.get("name", ""),
            base_confidence=float(row_confidence),
        )

        entries.append(
            PlayerRankingEntry(
                rank=int(row.get("rank") or row.get("ocr_rank") or index),
                server=int(server),
                alliance_tag=identity_quality.alliance_tag,
                player_name=identity_quality.player_name,
                hero_power=int(row["power"]),
                ocr_rank=row.get("ocr_rank"),
                computed_rank=row.get("computed_rank") or index,
                rank_warning=row.get("rank_warning"),
                server_confidence=server_confidence,
                server_source=server_source,
                server_warning=server_warning,
                snapshot_id=snapshot_id,
                confidence=float(identity_quality.confidence),
                source_file=row.get("source_file") or source_file,
                raw_text=row.get("raw_text"),
                parse_status=identity_quality.status,
                parse_warnings=identity_quality.warnings,
                parse_corrections=identity_quality.corrections,
                normalized_identity=identity_quality.normalized_input,
            )
        )

    return entries


def build_player_ranking_snapshot(
    rows: list[dict],
    server: int,
    ranking_type: str = "total_hero_power",
    snapshot_id: Optional[str] = None,
    source_file: Optional[str] = None,
    server_confidence: Optional[float] = None,
    server_source: Optional[str] = None,
    server_warning: Optional[str] = None,
) -> PlayerRankingSnapshot:
    """Build a structured THP snapshot from parsed OCR ranking rows."""
    entries = build_player_ranking_entries(
        rows=rows,
        server=server,
        snapshot_id=snapshot_id,
        source_file=source_file,
        server_confidence=server_confidence,
        server_source=server_source,
        server_warning=server_warning,
    )

    if server is None:
        raise ValueError("Cannot build player ranking snapshot without a validated server.")

    return PlayerRankingSnapshot(
        server=int(server),
        ranking_type=ranking_type,
        entries=entries,
        snapshot_id=snapshot_id,
        source_file=source_file,
    )
