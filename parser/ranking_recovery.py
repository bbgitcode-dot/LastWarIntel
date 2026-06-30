"""Ranking Guard Recovery for explainable ranking-type recovery.

This module sits after the Ranking Guard decision and before quarantine.  It is
conservative: it may recover only when row-level evidence is strong enough, and
it records the evidence instead of silently changing semantics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PLAYER_POWER_SOFT_MAX = 5_000_000_000


@dataclass(frozen=True)
class RankingRecoveryDecision:
    status: str
    target_ranking_type: str | None
    confidence: float
    reasons: list[str] = field(default_factory=list)

    @property
    def recovered(self) -> bool:
        return self.status == "recovered"

    @property
    def calibrated(self) -> bool:
        return self.status == "calibrated_pass"


def _power(row: dict[str, Any]) -> int | None:
    value = row.get("power") or row.get("hero_power") or row.get("alliance_power")
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _has_explicit_player_fields(row: dict[str, Any]) -> bool:
    """Return True only for parser rows with explicit THP player columns.

    Alliance-power rows often contain bracketed tags inside their alliance name,
    e.g. ``[PbC] Paradise Brewing Co``.  That is not enough to recover to THP.
    Recovery requires fields produced by the player-ranking builder.
    """
    alliance_tag = str(row.get("alliance_tag") or "").strip()
    player_name = str(row.get("player_name") or "").strip()
    return bool(alliance_tag or player_name or row.get("hero_power") is not None)


def _has_alliance_name_only_shape(row: dict[str, Any]) -> bool:
    name = str(row.get("name") or "").strip()
    return bool(name and not _has_explicit_player_fields(row))


def evaluate_ranking_recovery(
    row: dict[str, Any],
    *,
    assigned_ranking_type: str,
    expected_ranking_type: str | None,
    guard_reasons: list[str],
    guard_confidence: float,
) -> RankingRecoveryDecision:
    """Evaluate whether a Ranking Guard quarantine can be safely recovered.

    Outcomes:
    - ``recovered``: move the row to the expected ranking type.
    - ``calibrated_pass``: keep the row in the assigned ranking because the
      quarantine was caused by bracketed alliance names that mimic player tags.
    - ``quarantine``: leave the original guard decision unchanged.
    """
    value = _power(row)
    reasons = set(guard_reasons or [])

    if assigned_ranking_type == "alliance_power" and expected_ranking_type == "total_hero_power":
        explicit_player = _has_explicit_player_fields(row)
        player_scale = value is not None and value < PLAYER_POWER_SOFT_MAX

        # Safe reclassification: this row already carries explicit THP fields
        # and is not merely an alliance name containing a bracketed tag.
        if explicit_player and player_scale:
            evidence = [
                "explicit_player_fields",
                "player_scale_power",
                "ranking_guard_expected_total_hero_power",
                "read_only_guard_evidence",
            ]
            return RankingRecoveryDecision(
                status="recovered",
                target_ranking_type="total_hero_power",
                confidence=round(max(0.96, min(0.99, guard_confidence)), 4),
                reasons=evidence,
            )

        # Guard calibration: alliance-power lists commonly encode alliance tags
        # in the alliance name.  The Ranking Guard should not treat that alone as
        # player evidence.  This keeps real low-power alliances in Alliance Power
        # instead of filling quarantine with false positives.
        if _has_alliance_name_only_shape(row) and value is not None and value >= 1_000_000_000:
            evidence = [
                "alliance_name_only_shape",
                "no_explicit_player_fields",
                "bracketed_tag_not_sufficient_for_thp",
                "alliance_scale_power",
            ]
            confidence = 0.98 if value >= PLAYER_POWER_SOFT_MAX else 0.96
            return RankingRecoveryDecision(
                status="calibrated_pass",
                target_ranking_type="alliance_power",
                confidence=confidence,
                reasons=evidence,
            )

    return RankingRecoveryDecision(
        status="quarantine",
        target_ranking_type=None,
        confidence=0.0,
        reasons=["insufficient_recovery_evidence"],
    )


def annotate_recovery(row: dict[str, Any], decision: RankingRecoveryDecision) -> dict[str, Any]:
    recovered = dict(row)
    recovered["ranking_recovery_status"] = decision.status
    recovered["ranking_recovery_target"] = decision.target_ranking_type or ""
    recovered["ranking_recovery_confidence"] = decision.confidence
    recovered["ranking_recovery_reason"] = ";".join(decision.reasons)
    return recovered
