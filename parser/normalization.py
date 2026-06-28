"""OCR normalization utilities for ranking imports.

The normalization layer cleans OCR artefacts before structured parsing. It is
intentionally conservative for names and more permissive for numeric values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
import unicodedata
from typing import Optional


@dataclass(slots=True)
class NormalizationResult:
    value: str
    confidence: float = 1.0
    corrections: list[str] = field(default_factory=list)


def _penalize(confidence: float, amount: float) -> float:
    return max(0.0, round(confidence - amount, 4))


def _collapse_spaces(value: str) -> str:
    return " ".join(str(value or "").split())


class AllianceTagNormalizer:
    """Normalize OCR artefacts around alliance tags.

    Examples:
        ([ACEv] -> ACEv
        {ACEv]  -> ACEv
        [ACEv|  -> ACEv
    """

    _EDGE_NOISE = re.compile(r"^[\s\(\{\[\|]+|[\s\)\}\]\|]+$")
    _INNER_NOISE = re.compile(r"[^A-Za-z0-9]")

    def normalize(self, raw_tag: Optional[str]) -> NormalizationResult:
        original = _collapse_spaces(raw_tag or "")
        confidence = 1.0
        corrections: list[str] = []

        tag = original.strip()
        cleaned = self._EDGE_NOISE.sub("", tag)
        cleaned = self._INNER_NOISE.sub("", cleaned)

        if cleaned != original:
            confidence = _penalize(confidence, 0.05)
            corrections.append("alliance_tag_artifacts_removed")

        return NormalizationResult(cleaned, confidence, corrections)


class PlayerNameNormalizer:
    """Conservative player name normalizer.

    Names may legitimately contain digits. Therefore only very likely OCR
    artefacts are changed, such as a zero between two letters.
    """

    _EDGE_NOISE = re.compile(r"^[\s\[\]\(\)\{\}\|]+|[\s\[\]\(\)\{\}\|]+$")

    def normalize(self, raw_name: Optional[str]) -> NormalizationResult:
        original = _collapse_spaces(raw_name or "")
        confidence = 1.0
        corrections: list[str] = []

        name = unicodedata.normalize("NFKC", original)
        name = self._EDGE_NOISE.sub("", name).strip()

        if name != original:
            confidence = _penalize(confidence, 0.03)
            corrections.append("player_name_artifacts_removed")

        corrected = re.sub(r"(?<=[A-Za-z])0(?=[A-Za-z])", "o", name)
        if corrected != name:
            confidence = _penalize(confidence, 0.05)
            corrections.append("player_name_zero_between_letters")
            name = corrected

        # Common OCR issue for the sprint example: terminal 'rl' can be read
        # instead of 'ri' in names like Tarori -> Tarorl. Keep this narrow.
        corrected = re.sub(r"(?i)(?<=r)l$", "i", name)
        if corrected != name:
            confidence = _penalize(confidence, 0.04)
            corrections.append("player_name_terminal_l_after_r")
            name = corrected

        return NormalizationResult(name or "UNKNOWN", confidence, corrections)


class HeroPowerNormalizer:
    """Normalize numeric OCR fragments used for power values."""

    _NUMERIC_OCR_MAP = str.maketrans({
        "O": "0",
        "o": "0",
        "I": "1",
        "l": "1",
        "|": "1",
    })

    def normalize(self, raw_value: Optional[str]) -> NormalizationResult:
        original = str(raw_value or "")
        confidence = 1.0
        corrections: list[str] = []

        translated = original.translate(self._NUMERIC_OCR_MAP)
        digits = re.sub(r"\D", "", translated)

        if translated != original:
            confidence = _penalize(confidence, 0.04)
            corrections.append("hero_power_ocr_digits_corrected")

        if digits != re.sub(r"\D", "", original):
            confidence = _penalize(confidence, 0.02)
            corrections.append("hero_power_non_digits_removed")

        return NormalizationResult(digits, confidence, corrections)


def normalize_raw_player_identity_text(raw_name: str) -> NormalizationResult:
    """Normalize wrapper artefacts before tag/name splitting."""
    original = _collapse_spaces(raw_name or "")
    confidence = 1.0
    corrections: list[str] = []

    value = unicodedata.normalize("NFKC", original)
    replacements = {
        "｜": "|",
        "丨": "|",
        "【": "[",
        "】": "]",
    }

    for old, new in replacements.items():
        if old in value:
            value = value.replace(old, new)
            confidence = _penalize(confidence, 0.02)
            corrections.append("unicode_artifact_replaced")

    # Repair common broken tag wrappers without touching the actual name.
    repaired = re.sub(r"^[\(\{]\s*\[?", "[", value)
    repaired = re.sub(r"^\[\s*([A-Za-z0-9]{2,8})\s*[\|\}\)]", r"[\1]", repaired)
    repaired = re.sub(r"^\[\s*([A-Za-z0-9]{2,8})\s*\|", r"[\1]", repaired)

    if repaired != value:
        confidence = _penalize(confidence, 0.05)
        corrections.append("identity_tag_wrapper_repaired")
        value = repaired

    value = _collapse_spaces(value)
    return NormalizationResult(value, confidence, corrections)
