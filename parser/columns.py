"""Column reconstruction for Last War ranking rows.

Row alignment decides which OCR tokens belong to the same visible card row.
Column reconstruction decides what those tokens mean:

    rank | alliance tag | player name | power

The important design choice is that this layer works on OCR tokens with
geometry, not on already concatenated text. That lets us ignore visual badge
noise to the left of the alliance tag and repair common bracket/tag OCR damage
before identity parsing runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Iterable

from parser.alignment import OcrToken


_BRACKET_TAG_RE = re.compile(r"\[\s*([A-Za-z0-9]{2,6})\s*\]")
# Examples seen in screenshots: ``IPbC] Monkopeace`` or ``IIVE] Name``.
_MISSING_OPEN_BRACKET_TAG_RE = re.compile(r"(?<![A-Za-z0-9])([A-Za-z0-9Il|]{3,7})\]")
_SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class ReconstructedColumns:
    """Structured fields reconstructed from one aligned OCR row."""

    raw_name: str
    player_name_text: str
    alliance_tag: str | None = None
    warnings: list[str] = field(default_factory=list)
    corrections: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _TagMatch:
    tag: str
    start: int
    end: int
    correction: str | None = None


def _clean_spaces(value: str) -> str:
    return _SPACE_RE.sub(" ", str(value or "")).strip()


def _normalize_tag_candidate(value: str) -> str | None:
    candidate = re.sub(r"[^A-Za-z0-9]", "", str(value or "")).strip()
    if len(candidate) < 2 or len(candidate) > 6:
        return None

    # EasyOCR often glues a leading vertical stroke to malformed tags:
    # ``IPbC]`` should be interpreted as ``PbC]``. Do this only for
    # longer candidates so real short tags like ``IVE`` remain untouched.
    if len(candidate) >= 4 and candidate[0] in {"I", "l", "1", "|"}:
        stripped = candidate[1:]
        if len(stripped) >= 2 and any(ch.isalpha() for ch in stripped):
            candidate = stripped

    if not any(ch.isalpha() for ch in candidate):
        return None

    return candidate


def _find_tag(text: str) -> _TagMatch | None:
    text = str(text or "")

    match = _BRACKET_TAG_RE.search(text)
    if match:
        tag = _normalize_tag_candidate(match.group(1))
        if tag:
            return _TagMatch(tag=tag, start=match.start(), end=match.end())

    match = _MISSING_OPEN_BRACKET_TAG_RE.search(text)
    if match:
        tag = _normalize_tag_candidate(match.group(1))
        if tag:
            return _TagMatch(
                tag=tag,
                start=match.start(),
                end=match.end(),
                correction="missing_open_alliance_bracket_repaired",
            )

    return None


def _looks_like_visual_badge_noise(text: str) -> bool:
    """Return True for small UI/badge fragments that are not player names.

    These fragments often sit between the rank and alliance tag and contain a
    mix of CJK-looking OCR debris, punctuation and digits, e.g. ``0咀#5``.
    We intentionally keep readable Latin words and Hangul-only strings because
    those can be legitimate player names when no alliance tag was detected.
    """
    value = _clean_spaces(text)
    if not value:
        return True
    if len(value) <= 2 and not any(ch.isalnum() for ch in value):
        return True

    latin = sum(1 for ch in value if "A" <= ch.upper() <= "Z")
    digits = sum(1 for ch in value if ch.isdigit())
    hangul = sum(1 for ch in value if "\uac00" <= ch <= "\ud7af")
    alnum = sum(1 for ch in value if ch.isalnum())
    symbols = len(value) - alnum - sum(1 for ch in value if ch.isspace())

    if hangul and latin == 0 and symbols == 0:
        return False

    # Short OCR shards with many symbols/digits are almost always badge noise.
    if len(value) <= 8 and symbols >= 1 and (digits >= 1 or latin <= 1):
        return True

    # CJK debris plus digits but no meaningful Latin/Hangul player text.
    non_ascii = sum(1 for ch in value if ord(ch) > 127)
    if len(value) <= 8 and non_ascii >= 1 and latin <= 1 and digits >= 1:
        return True

    return False


def reconstruct_columns(
    tokens: Iterable[OcrToken],
    *,
    rank_token: OcrToken | None,
    power_token: OcrToken | None,
    is_rank,
    is_power,
) -> ReconstructedColumns:
    """Reconstruct alliance/name columns from a row's OCR tokens."""
    warnings: list[str] = []
    corrections: list[str] = []

    content_tokens: list[OcrToken] = []
    for token in sorted(tokens, key=lambda item: item.cx):
        if power_token is not None and token is power_token:
            continue
        if rank_token is not None and token is rank_token:
            continue
        if power_token is not None and token.cx >= power_token.cx:
            continue
        if is_rank(str(token.text)) or is_power(str(token.text)):
            continue
        if str(token.text or "").strip():
            content_tokens.append(token)

    alliance_tag: str | None = None
    name_parts: list[str] = []
    tag_found = False

    for index, token in enumerate(content_tokens):
        text = _clean_spaces(token.text)
        if not text:
            continue

        tag_match = _find_tag(text)
        if tag_match:
            alliance_tag = tag_match.tag
            tag_found = True
            if tag_match.correction:
                corrections.append(tag_match.correction)

            # Tokens before the alliance tag are visual badge/decoration noise.
            if index > 0:
                corrections.append("tokens_before_alliance_column_ignored")

            remainder = _clean_spaces(text[tag_match.end:])
            if remainder:
                name_parts.append(remainder)
            continue

        if not tag_found:
            # Before the alliance column, ignore badge noise. If there is no tag
            # in the entire row, readable tokens will be collected in the second
            # pass below.
            continue

        name_parts.append(text)

    if not tag_found:
        warnings.append("alliance_column_not_detected")
        for token in content_tokens:
            text = _clean_spaces(token.text)
            if not text:
                continue
            if _looks_like_visual_badge_noise(text):
                corrections.append("visual_badge_noise_ignored")
                continue
            name_parts.append(text)

    player_name_text = _clean_spaces(" ".join(name_parts))
    raw_name = f"[{alliance_tag}] {player_name_text}" if alliance_tag else player_name_text

    if not player_name_text:
        warnings.append("player_name_column_empty")

    return ReconstructedColumns(
        raw_name=raw_name,
        player_name_text=player_name_text,
        alliance_tag=alliance_tag,
        warnings=list(dict.fromkeys(warnings)),
        corrections=list(dict.fromkeys(corrections)),
    )
