"""Player identity parsing and quality calibration for OCR ranking rows.

The goal of this layer is not to prove that a player identity is perfect.
It decides whether the parsed identity is directly usable (VALID) or should
remain in manual review (REVIEW). OCR is allowed to be imperfect as long as
important structured fields are actionable and traceable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import re
import unicodedata


_TAG_RE = re.compile(r"\[\s*([A-Za-z0-9]{2,6})\s*\]")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_SPACE_RE = re.compile(r"\s+")

# Obvious non-name UI fragments that sometimes leak into the name region.
_NOISE_WORDS = {
    "warzone",
    "ranking",
    "commander",
    "power",
    "total",
    "hero",
    "alliance",
    "updates",
    "leaderboard",
}


@dataclass(frozen=True)
class PlayerIdentityQuality:
    alliance_tag: Optional[str]
    player_name: str
    confidence: float
    status: str
    warnings: list[str] = field(default_factory=list)
    corrections: list[str] = field(default_factory=list)
    normalized_input: str = ""


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = _CONTROL_RE.sub("", text)
    text = text.replace("｜", "|")
    text = _SPACE_RE.sub(" ", text).strip()
    return text


def _looks_like_noise(name: str) -> bool:
    stripped = name.strip()
    if not stripped:
        return True
    lower = stripped.lower()
    if lower in _NOISE_WORDS:
        return True
    if any(word in lower for word in ("warzone", "total hero", "alliance power")):
        return True
    # Pure punctuation / OCR symbols are not actionable identities.
    useful = [ch for ch in stripped if ch.isalnum() or ord(ch) > 127]
    return len(useful) == 0


def parse_player_identity_quality(raw_name: str, base_confidence: float = 1.0) -> PlayerIdentityQuality:
    """Parse a raw OCR name into tag, player name and calibrated status.

    Calibration policy for the transfer baseline:
    - Prefix garbage before a valid [TAG] is corrected, not automatically REVIEW.
    - CJK names are accepted as usable text when OCR returns actual characters.
    - Missing alliance tag is allowed; it can mean alliance-less player.
    - REVIEW is reserved for identities that are not actionable.
    """
    warnings: list[str] = []
    corrections: list[str] = []
    normalized = _normalize_text(raw_name)

    alliance_tag: Optional[str] = None
    player_part = normalized

    match = _TAG_RE.search(normalized)
    if match:
        alliance_tag = match.group(1).strip()
        before = normalized[: match.start()].strip()
        after = normalized[match.end() :].strip()
        player_part = after
        if before:
            corrections.append("prefix_before_alliance_tag_ignored")
    else:
        # Not every player must have an alliance tag. Keep it valid if the name
        # itself is readable, but record this because it matters for recruitment.
        warnings.append("alliance_tag_missing")

    # Remove trailing power/rank fragments if OCR grouped too much text.
    player_part = re.sub(r"\b\d{7,}\b.*$", "", player_part).strip()
    player_part = _SPACE_RE.sub(" ", player_part)

    if _looks_like_noise(player_part):
        player_name = "UNKNOWN"
        warnings.append("player_name_unusable")
    else:
        player_name = player_part

    confidence = max(0.0, min(1.0, float(base_confidence)))
    if player_name == "UNKNOWN":
        confidence = min(confidence, 0.25)
    elif alliance_tag:
        confidence = max(confidence, 0.80)
    else:
        # Name without tag is still usable, just slightly less certain.
        confidence = min(max(confidence, 0.65), 0.85)

    review_reasons = {
        "player_name_unusable",
    }
    if confidence < 0.35:
        warnings.append("low_identity_confidence")

    status = "REVIEW" if any(reason in warnings for reason in review_reasons) or confidence < 0.35 else "VALID"

    return PlayerIdentityQuality(
        alliance_tag=alliance_tag,
        player_name=player_name,
        confidence=round(confidence, 4),
        status=status,
        warnings=list(dict.fromkeys(warnings)),
        corrections=list(dict.fromkeys(corrections)),
        normalized_input=normalized,
    )
