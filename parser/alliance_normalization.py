"""Alliance tag normalization for OCR-derived rankings.

OCR often drops one character from short alliance tags, for example:

    PBC -> PC
    IVE -> IV
    PWW -> PW

This module performs conservative, vocabulary-aware normalization. It never
inventories a global list of alliances. Instead it uses the tags visible in the
same snapshot or validation dataset as the allowed vocabulary and only repairs
an OCR tag when exactly one plausible candidate exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
import re
from typing import Iterable


_TAG_CLEAN_RE = re.compile(r"[^A-Za-z0-9]")


@dataclass(frozen=True)
class AllianceNormalizationResult:
    raw: str
    value: str
    confidence: float
    match_type: str
    corrections: list[str] = field(default_factory=list)


def clean_alliance_tag(value: object) -> str:
    """Normalize OCR wrapper/noise around an alliance tag to uppercase text."""
    text = str(value or "").strip()
    if not text or text.lower() == "nan":
        return ""

    # Accept both a bare tag and bracketed/broken tag fragments.
    bracket = re.search(r"\[\s*([A-Za-z0-9]{2,8})\s*\]", text)
    if bracket:
        text = bracket.group(1)
    else:
        trailing = re.search(r"([A-Za-z0-9Il|]{2,8})\]", text)
        if trailing:
            text = trailing.group(1)

    text = text.replace("|", "I").replace("l", "I")
    return _TAG_CLEAN_RE.sub("", text).upper()


def _is_subsequence(short: str, long: str) -> bool:
    if not short:
        return False
    pos = 0
    for char in long:
        if pos < len(short) and short[pos] == char:
            pos += 1
    return pos == len(short)


def _levenshtein_one_or_less(a: str, b: str) -> bool:
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False

    # Cheap exact edit-distance <= 1 check for short tags.
    if len(a) == len(b):
        return sum(1 for x, y in zip(a, b) if x != y) <= 1

    shorter, longer = (a, b) if len(a) < len(b) else (b, a)
    i = j = edits = 0
    while i < len(shorter) and j < len(longer):
        if shorter[i] == longer[j]:
            i += 1
            j += 1
        else:
            edits += 1
            if edits > 1:
                return False
            j += 1
    return True


def build_alliance_vocabulary(*tag_sets: Iterable[object]) -> list[str]:
    """Build a stable vocabulary from observed or expected alliance tags."""
    result: list[str] = []
    seen: set[str] = set()
    for tag_set in tag_sets:
        for raw in tag_set:
            tag = clean_alliance_tag(raw)
            if len(tag) < 2:
                continue
            # One-character OCR shards are not useful vocabulary entries.
            if tag not in seen:
                seen.add(tag)
                result.append(tag)
    return result


def normalize_alliance_tag(value: object, vocabulary: Iterable[object] | None = None) -> AllianceNormalizationResult:
    """Normalize an OCR alliance tag against an optional local vocabulary.

    The function is intentionally conservative: fuzzy correction is only applied
    when exactly one candidate is plausible. Ambiguous tags remain unchanged and
    are marked as ambiguous instead of being guessed.
    """
    raw = str(value or "")
    tag = clean_alliance_tag(raw)
    if not tag:
        return AllianceNormalizationResult(raw=raw, value="", confidence=0.0, match_type="missing")

    vocab = build_alliance_vocabulary(vocabulary or [])
    if not vocab:
        return AllianceNormalizationResult(raw=raw, value=tag, confidence=0.75, match_type="cleaned")

    if tag in vocab:
        return AllianceNormalizationResult(raw=raw, value=tag, confidence=1.0, match_type="exact")

    candidates: list[tuple[str, float, str]] = []
    for candidate in vocab:
        score = SequenceMatcher(None, tag, candidate).ratio()
        if _levenshtein_one_or_less(tag, candidate):
            candidates.append((candidate, max(score, 0.92), "edit_distance_1"))
            continue
        if len(tag) >= 2 and len(candidate) >= 3 and _is_subsequence(tag, candidate):
            candidates.append((candidate, max(score, 0.88), "subsequence"))
            continue
        if len(tag) >= 3 and score >= 0.82:
            candidates.append((candidate, score, "similarity"))

    # Deduplicate and sort by confidence descending.
    best_by_candidate: dict[str, tuple[str, float, str]] = {}
    for candidate, score, reason in candidates:
        if candidate not in best_by_candidate or score > best_by_candidate[candidate][1]:
            best_by_candidate[candidate] = (candidate, score, reason)
    candidates = sorted(best_by_candidate.values(), key=lambda item: item[1], reverse=True)

    if not candidates:
        return AllianceNormalizationResult(raw=raw, value=tag, confidence=0.55, match_type="unmatched")

    if len(candidates) == 1 or (candidates[0][1] - candidates[1][1] >= 0.12):
        candidate, score, reason = candidates[0]
        return AllianceNormalizationResult(
            raw=raw,
            value=candidate,
            confidence=round(score, 4),
            match_type="normalized",
            corrections=[f"alliance_tag_{reason}:{tag}->{candidate}"],
        )

    return AllianceNormalizationResult(raw=raw, value=tag, confidence=0.45, match_type="ambiguous")
