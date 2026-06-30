"""Sentinel Ranking Guard for import-time ranking integrity.

The Ranking Guard is a Data Guard module for semantic ranking-type fit. It does
not repair rows or guess a better destination. When a row does not have enough
intrinsic evidence for its assigned ranking type, it is moved to quarantine for
review.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

PLAYER_POWER_SOFT_MAX = 5_000_000_000
ALLIANCE_POWER_SOFT_MIN = 1_000_000_000
ALLIANCE_POWER_STRONG_MIN = 10_000_000_000

KNOWN_RANKING_TYPES = {"total_hero_power", "alliance_power"}
QUARANTINE_KEY = ("REVIEW", "ranking_guard_quarantine")


@dataclass(frozen=True)
class RankingGuardDecision:
    assigned_ranking_type: str
    expected_ranking_type: str | None
    status: str
    confidence: float
    reasons: list[str] = field(default_factory=list)

    @property
    def should_quarantine(self) -> bool:
        return self.status == "quarantine"


def _power(row: dict[str, Any]) -> int | None:
    value = row.get("power") or row.get("hero_power") or row.get("alliance_power")
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _text(row: dict[str, Any]) -> str:
    parts = [
        row.get("alliance_tag"),
        row.get("player_name"),
        row.get("name"),
        row.get("raw_text"),
    ]
    return " ".join(str(value) for value in parts if value is not None)


def _has_player_tag(row: dict[str, Any]) -> bool:
    tag = str(row.get("alliance_tag") or "").strip()
    if tag:
        return True
    text = _text(row)
    return re.search(r"\[[A-Za-z0-9]{1,8}\]", text) is not None


def _has_player_name(row: dict[str, Any]) -> bool:
    player_name = str(row.get("player_name") or "").strip()
    if player_name:
        return True
    name = str(row.get("name") or "").strip()
    if not name:
        return False
    # Generic alliance-power rows can have a name too. Player shape is stronger
    # when the row contains the in-game alliance tag prefix.
    return _has_player_tag(row) and len(name) > 3


def _looks_like_total_hero_power(row: dict[str, Any]) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    value = _power(row)

    if _has_player_tag(row):
        score += 0.45
        reasons.append("player_alliance_tag_shape")
    if _has_player_name(row):
        score += 0.25
        reasons.append("player_name_shape")
    if value is not None and value < PLAYER_POWER_SOFT_MAX:
        score += 0.25
        reasons.append("player_scale_power")
    if row.get("hero_power") is not None:
        score += 0.15
        reasons.append("hero_power_field_present")

    return min(score, 1.0), reasons


def _looks_like_alliance_power(row: dict[str, Any]) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    value = _power(row)
    name = str(row.get("name") or "").strip()

    if name:
        score += 0.20
        reasons.append("alliance_name_present")
    if value is not None and value >= ALLIANCE_POWER_SOFT_MIN:
        score += 0.25
        reasons.append("alliance_scale_power")
    if value is not None and value >= ALLIANCE_POWER_STRONG_MIN:
        score += 0.35
        reasons.append("strong_alliance_scale_power")
    if not _has_player_tag(row):
        score += 0.20
        reasons.append("no_player_tag_shape")

    return min(score, 1.0), reasons


def evaluate_ranking_row(row: dict[str, Any], assigned_ranking_type: str) -> RankingGuardDecision:
    """Evaluate whether one parsed row semantically fits its assigned ranking."""
    if assigned_ranking_type not in KNOWN_RANKING_TYPES:
        return RankingGuardDecision(
            assigned_ranking_type=assigned_ranking_type,
            expected_ranking_type=None,
            status="pass",
            confidence=1.0,
            reasons=["ranking_type_not_guarded"],
        )

    thp_score, thp_reasons = _looks_like_total_hero_power(row)
    alliance_score, alliance_reasons = _looks_like_alliance_power(row)
    value = _power(row)

    reasons: list[str] = []
    if value is None:
        return RankingGuardDecision(
            assigned_ranking_type=assigned_ranking_type,
            expected_ranking_type=None,
            status="quarantine",
            confidence=0.0,
            reasons=["missing_power"],
        )

    if assigned_ranking_type == "alliance_power":
        if thp_score >= 0.70 and thp_score > alliance_score + 0.20:
            reasons.extend(thp_reasons)
            reasons.append("assigned_alliance_power_but_row_is_thp_shaped")
            return RankingGuardDecision(
                assigned_ranking_type=assigned_ranking_type,
                expected_ranking_type="total_hero_power",
                status="quarantine",
                confidence=round(thp_score, 4),
                reasons=list(dict.fromkeys(reasons)),
            )
        if not str(row.get("name") or "").strip():
            return RankingGuardDecision(
                assigned_ranking_type=assigned_ranking_type,
                expected_ranking_type=None,
                status="quarantine",
                confidence=round(alliance_score, 4),
                reasons=["missing_alliance_name"],
            )

    if assigned_ranking_type == "total_hero_power":
        if alliance_score >= 0.75 and alliance_score > thp_score + 0.20:
            reasons.extend(alliance_reasons)
            reasons.append("assigned_total_hero_power_but_row_is_alliance_shaped")
            return RankingGuardDecision(
                assigned_ranking_type=assigned_ranking_type,
                expected_ranking_type="alliance_power",
                status="quarantine",
                confidence=round(alliance_score, 4),
                reasons=list(dict.fromkeys(reasons)),
            )
        if not _has_player_name(row):
            return RankingGuardDecision(
                assigned_ranking_type=assigned_ranking_type,
                expected_ranking_type=None,
                status="quarantine",
                confidence=round(thp_score, 4),
                reasons=["missing_player_identity"],
            )

    return RankingGuardDecision(
        assigned_ranking_type=assigned_ranking_type,
        expected_ranking_type=assigned_ranking_type,
        status="pass",
        confidence=round(max(thp_score if assigned_ranking_type == "total_hero_power" else alliance_score, 0.01), 4),
        reasons=["ranking_type_fit_validated"],
    )


def _mark_quarantined(row: dict[str, Any], *, server: object, decision: RankingGuardDecision) -> dict[str, Any]:
    quarantined = dict(row)
    previous_warning = str(quarantined.get("ranking_guard_warning") or "").strip()
    reason = ";".join(decision.reasons)
    warning = f"ranking_type_conflict:{reason}" if reason else "ranking_type_conflict"
    quarantined["original_server"] = server if isinstance(server, int) else quarantined.get("server")
    quarantined["original_ranking_type"] = decision.assigned_ranking_type
    quarantined["ranking_type"] = decision.assigned_ranking_type
    quarantined["expected_ranking_type"] = decision.expected_ranking_type or "unknown"
    quarantined["ranking_guard_status"] = decision.status
    quarantined["ranking_guard_confidence"] = decision.confidence
    quarantined["ranking_guard_reason"] = reason
    quarantined["ranking_guard_warning"] = warning if not previous_warning else f"{previous_warning};{warning}"
    quarantined["quarantine_reason"] = "ranking_type_conflict"
    return quarantined


def apply_ranking_guard(
    grouped: dict[tuple[object, str], list[dict[str, Any]]]
) -> dict[tuple[object, str], list[dict[str, Any]]]:
    """Quarantine rows that do not semantically fit their ranking type.

    This function never moves rows into a guessed corrected ranking. It keeps
    trusted rows in place and moves suspicious rows to REVIEW/ranking_guard
    quarantine with explanatory metadata.
    """
    guarded: dict[tuple[object, str], list[dict[str, Any]]] = {}
    quarantined_rows: list[dict[str, Any]] = []

    for key, rows in grouped.items():
        server, ranking_type = key
        if ranking_type not in KNOWN_RANKING_TYPES:
            guarded.setdefault(key, []).extend(rows)
            continue

        for row in rows:
            decision = evaluate_ranking_row(row, ranking_type)
            if decision.should_quarantine:
                quarantined_rows.append(_mark_quarantined(row, server=server, decision=decision))
                continue

            row["ranking_guard_status"] = "validated"
            row["ranking_guard_confidence"] = decision.confidence
            guarded.setdefault(key, []).append(row)

    if quarantined_rows:
        guarded.setdefault(QUARANTINE_KEY, []).extend(quarantined_rows)

    return guarded
