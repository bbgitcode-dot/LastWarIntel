"""Quality gate helpers for OCR-derived player identities.

This module is intentionally conservative. OCR output is allowed to be bad,
but bad OCR must never be imported silently as a trusted player identity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
import unicodedata
from typing import Optional

from parser.normalization import (
    AllianceTagNormalizer,
    PlayerNameNormalizer,
    normalize_raw_player_identity_text,
)


_TAG_ANYWHERE = re.compile(
    r"(?P<prefix>.*?)"
    r"[\(\{\[]?\s*\[\s*(?P<tag>[A-Za-z0-9]{2,8})\s*[\]\|\}\)]\s*"
    r"(?P<name>.*)$"
)

_VALID_LATIN_NAME = re.compile(r"[A-Za-z0-9]")
_GARBAGE_MARKS = {"?", "�", "□", "■", "▯", "▒", "�"}


@dataclass(slots=True)
class PlayerIdentityQuality:
    alliance_tag: Optional[str]
    player_name: str
    confidence: float
    status: str
    warnings: list[str] = field(default_factory=list)
    corrections: list[str] = field(default_factory=list)
    raw_input: str = ""
    normalized_input: str = ""

    @property
    def warnings_text(self) -> str:
        return ";".join(self.warnings)

    @property
    def corrections_text(self) -> str:
        return ";".join(self.corrections)


def _penalize(confidence: float, amount: float) -> float:
    return max(0.0, round(confidence - amount, 4))


def _contains_garbage_marks(value: str) -> bool:
    return any(mark in value for mark in _GARBAGE_MARKS)


def _has_latin_or_digit(value: str) -> bool:
    return bool(_VALID_LATIN_NAME.search(value or ""))


def _is_effectively_empty_name(value: str) -> bool:
    cleaned = str(value or "").strip()
    if not cleaned:
        return True
    if cleaned.upper() in {"UNKNOWN", "N/A", "NA", "NONE", "NULL"}:
        return True
    stripped_symbols = "".join(
        ch for ch in cleaned
        if unicodedata.category(ch)[0] not in {"P", "S", "Z", "C"}
    )
    return not stripped_symbols


def _is_untrusted_ocr_name(value: str) -> bool:
    """Return True when OCR name should not be trusted as identity.

    Asian names are often not read by the OCR stack used in the current import
    flow. We therefore do not invent an identity from symbol noise. If OCR does
    provide a usable latin/digit representation, it is kept. Otherwise the row
    must go to review with player_name=UNKNOWN.
    """
    if _is_effectively_empty_name(value):
        return True
    if _contains_garbage_marks(value):
        return True
    # If the output has no latin letters or digits, downstream matching cannot
    # use it safely with the current data model. Keep the row via rank/power/tag
    # but mark player identity unknown.
    if not _has_latin_or_digit(value):
        return True
    return False


class PlayerIdentityQualityGate:
    """Extract alliance tag and player name with explicit review status."""

    def __init__(self) -> None:
        self._tag_normalizer = AllianceTagNormalizer()
        self._name_normalizer = PlayerNameNormalizer()

    def parse(self, raw_name: Optional[str], base_confidence: float = 1.0) -> PlayerIdentityQuality:
        raw = str(raw_name or "")
        normalized_identity = normalize_raw_player_identity_text(raw)
        text = normalized_identity.value
        confidence = min(float(base_confidence), float(normalized_identity.confidence))
        warnings: list[str] = []
        corrections: list[str] = list(normalized_identity.corrections)

        alliance_tag: Optional[str] = None
        raw_player_name = text

        match = _TAG_ANYWHERE.match(text)
        if match:
            prefix = (match.group("prefix") or "").strip()
            raw_tag = match.group("tag") or ""
            raw_player_name = (match.group("name") or "").strip()

            tag_result = self._tag_normalizer.normalize(raw_tag)
            alliance_tag = tag_result.value or None
            confidence = min(confidence, tag_result.confidence)
            corrections.extend(tag_result.corrections)

            if prefix:
                warnings.append("prefix_before_alliance_tag_ignored")
                confidence = _penalize(confidence, 0.08)
        else:
            warnings.append("missing_alliance_tag")
            confidence = _penalize(confidence, 0.10)

        name_result = self._name_normalizer.normalize(raw_player_name)
        player_name = name_result.value or "UNKNOWN"
        confidence = min(confidence, name_result.confidence)
        corrections.extend(name_result.corrections)

        if _is_untrusted_ocr_name(player_name):
            player_name = "UNKNOWN"
            warnings.append("untrusted_or_unreadable_player_name")
            confidence = _penalize(confidence, 0.25)

        if player_name == "UNKNOWN":
            warnings.append("player_identity_requires_review")

        if not alliance_tag:
            warnings.append("alliance_tag_requires_review")

        # De-duplicate while preserving order.
        warnings = list(dict.fromkeys(warnings))
        corrections = list(dict.fromkeys(corrections))

        status = "VALID"
        if warnings or confidence < 0.80:
            status = "REVIEW"

        return PlayerIdentityQuality(
            alliance_tag=alliance_tag,
            player_name=player_name,
            confidence=round(confidence, 4),
            status=status,
            warnings=warnings,
            corrections=corrections,
            raw_input=raw,
            normalized_input=text,
        )


_DEFAULT_GATE = PlayerIdentityQualityGate()


def parse_player_identity_quality(raw_name: Optional[str], base_confidence: float = 1.0) -> PlayerIdentityQuality:
    return _DEFAULT_GATE.parse(raw_name, base_confidence=base_confidence)
