"""Structured parser for Total Hero Power ranking rows."""

from __future__ import annotations

import re
from typing import Optional

from models.player_ranking import PlayerRankingEntry, PlayerRankingSnapshot
from parser.normalization import (
    AllianceTagNormalizer,
    PlayerNameNormalizer,
    normalize_raw_player_identity_text,
)

_ALLIANCE_TAG_NORMALIZER = AllianceTagNormalizer()
_PLAYER_NAME_NORMALIZER = PlayerNameNormalizer()


_TAG_AT_START = re.compile(
    r"^\s*[\(\{\[]?\s*\[?\s*(?P<tag>[A-Za-z0-9]{2,8})\s*[\]\|\}\)]\s*(?P<name>.*)$"
)


def split_alliance_tag_and_player_name_with_confidence(
    raw_name: str,
) -> tuple[Optional[str], str, float]:
    """Split a raw OCR name into normalized alliance tag, name and confidence."""
    identity = normalize_raw_player_identity_text(raw_name)
    name = identity.value
    confidence = identity.confidence

    if not name:
        return None, "UNKNOWN", confidence

    match = _TAG_AT_START.match(name)
    if not match:
        player = _PLAYER_NAME_NORMALIZER.normalize(name)
        return None, player.value, min(confidence, player.confidence)

    raw_tag = match.group("tag").strip()
    raw_player_name = match.group("name").strip() or "UNKNOWN"

    tag = _ALLIANCE_TAG_NORMALIZER.normalize(raw_tag)
    player = _PLAYER_NAME_NORMALIZER.normalize(raw_player_name)

    return (
        tag.value or None,
        player.value or "UNKNOWN",
        min(confidence, tag.confidence, player.confidence),
    )


def split_alliance_tag_and_player_name(raw_name: str) -> tuple[Optional[str], str]:
    """Backward-compatible split helper used by existing callers/tests."""
    alliance_tag, player_name, _confidence = split_alliance_tag_and_player_name_with_confidence(raw_name)
    return alliance_tag, player_name


def build_player_ranking_entries(
    rows: list[dict],
    server: int,
    snapshot_id: Optional[str] = None,
    source_file: Optional[str] = None,
) -> list[PlayerRankingEntry]:
    """Convert legacy parsed OCR rows into structured THP entries."""
    entries: list[PlayerRankingEntry] = []

    sorted_rows = sorted(
        [row for row in rows if row.get("power")],
        key=lambda row: row["power"],
        reverse=True,
    )

    for index, row in enumerate(sorted_rows, start=1):
        alliance_tag, player_name, normalization_confidence = (
            split_alliance_tag_and_player_name_with_confidence(row.get("name", ""))
        )

        confidence = row.get("confidence")
        if confidence is None:
            confidence = 1.0
        confidence = min(float(confidence), float(normalization_confidence))

        entries.append(
            PlayerRankingEntry(
                rank=int(row.get("rank") or index),
                server=int(server),
                alliance_tag=alliance_tag,
                player_name=player_name,
                hero_power=int(row["power"]),
                snapshot_id=snapshot_id,
                confidence=float(confidence),
                source_file=row.get("source_file") or source_file,
                raw_text=row.get("raw_text"),
            )
        )

    return entries


def build_player_ranking_snapshot(
    rows: list[dict],
    server: int,
    ranking_type: str = "total_hero_power",
    snapshot_id: Optional[str] = None,
    source_file: Optional[str] = None,
) -> PlayerRankingSnapshot:
    """Build a structured THP snapshot from parsed OCR ranking rows."""
    entries = build_player_ranking_entries(
        rows=rows,
        server=server,
        snapshot_id=snapshot_id,
        source_file=source_file,
    )

    return PlayerRankingSnapshot(
        server=int(server),
        ranking_type=ranking_type,
        entries=entries,
        snapshot_id=snapshot_id,
        source_file=source_file,
    )
