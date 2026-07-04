"""Identity Guard primitives for Sentinel Operational Truth.

Identity Guard is intentionally stricter than OCR matching.  OCR similarity may
be useful for review suggestions, but alliance tags and player names must retain
raw display fidelity for long-term transfer/player history.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re

_CONFUSABLE_RE = re.compile(r"[Il1|0OozZ]")


@dataclass(frozen=True)
class IdentityGuardResult:
    status: str
    risk: str
    warnings: list[str] = field(default_factory=list)
    case_sensitive_alliance_tag: str = ""
    canonical_alliance_tag: str = ""
    observed_player_name: str = ""


def evaluate_identity_fidelity(
    *,
    observed_alliance_tag: object = "",
    canonical_alliance_tag: object = "",
    observed_player_name: object = "",
) -> IdentityGuardResult:
    """Evaluate whether an OCR identity is safe for historical linkage.

    This function does not correct anything.  It records risk.  In particular,
    short alliance tags are case-sensitive Last War identifiers: DAY and daY are
    not interchangeable Operational Truth even when their canonical uppercase
    forms look the same.
    """
    raw_tag = str(observed_alliance_tag or "").strip()
    canonical_tag = str(canonical_alliance_tag or "").strip()
    player = str(observed_player_name or "").strip()
    warnings: list[str] = []

    if raw_tag and canonical_tag and raw_tag != canonical_tag:
        warnings.append("alliance_tag_canonicalization_changed_display")
    if raw_tag and raw_tag.upper() == canonical_tag.upper() and raw_tag != canonical_tag:
        warnings.append("alliance_tag_case_sensitive_difference")
    if len(raw_tag) > 5:
        warnings.append("alliance_tag_length_unusual")
    if player and _CONFUSABLE_RE.search(player):
        warnings.append("player_name_contains_ocr_confusables")
    if not player or player.upper() == "UNKNOWN":
        warnings.append("player_name_not_fidelity_safe")

    high_risk = {
        "alliance_tag_case_sensitive_difference",
        "player_name_not_fidelity_safe",
    }
    medium_risk = {
        "alliance_tag_canonicalization_changed_display",
        "player_name_contains_ocr_confusables",
        "alliance_tag_length_unusual",
    }
    if any(item in warnings for item in high_risk):
        risk = "high"
        status = "REVIEW"
    elif any(item in warnings for item in medium_risk):
        risk = "medium"
        status = "WARN"
    else:
        risk = "low"
        status = "PASS"

    return IdentityGuardResult(
        status=status,
        risk=risk,
        warnings=list(dict.fromkeys(warnings)),
        case_sensitive_alliance_tag=raw_tag,
        canonical_alliance_tag=canonical_tag,
        observed_player_name=player,
    )
