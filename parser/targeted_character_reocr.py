"""Targeted character re-OCR support for Gold Fidelity validation.

This module is deliberately conservative.  It never canonicalizes a player or
alliance identity from context.  It creates additional screenshot evidence for
specific character positions that were already flagged by the Character
Verification layer.

The first implementation is optimized for fixed Last War ranking screenshots
(normalized to the configured 600x1064 baseline).  It can run with any OCR
provider that implements the Sentinel provider interface and can also be tested
with a tiny fake provider.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
import json
from pathlib import Path
from typing import Any, Callable, Iterable

try:  # Pillow is already required by the importer, but keep imports lazy-safe.
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps
except Exception:  # pragma: no cover - import environment dependent
    Image = None  # type: ignore
    ImageEnhance = None  # type: ignore
    ImageFilter = None  # type: ignore
    ImageOps = None  # type: ignore


@dataclass(frozen=True)
class ReOcrTarget:
    field: str
    position: int
    expected: str = ""
    observed: str = ""
    reason: str = ""
    group: str = ""


@dataclass(frozen=True)
class CharacterVote:
    variant: str
    text: str
    confidence: float
    char: str = ""


@dataclass(frozen=True)
class CharacterVerificationEvidence:
    field: str
    position: int
    expected: str
    observed: str
    screenshot: str
    row_slot: int | None
    crop_box: tuple[int, int, int, int] | None
    status: str
    selected: str = ""
    confidence: float = 0.0
    votes: tuple[CharacterVote, ...] = field(default_factory=tuple)
    reason: str = ""

    @property
    def supports_expected(self) -> bool:
        return bool(self.expected) and self.status == "verified_expected"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["votes"] = [asdict(vote) for vote in self.votes]
        return payload


def parse_reocr_targets(value: Any) -> list[ReOcrTarget]:
    """Parse a JSON target list produced by parser.character_verification."""
    if not value or str(value) == "[]":
        return []
    try:
        raw = json.loads(str(value))
    except Exception:
        return []
    targets: list[ReOcrTarget] = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        targets.append(ReOcrTarget(
            field=str(item.get("field") or ""),
            position=int(item.get("position") or 0),
            expected=str(item.get("expected") or ""),
            observed=str(item.get("observed") or ""),
            reason=str(item.get("reason") or ""),
            group=str(item.get("group") or ""),
        ))
    return targets


def _ranking_row_box(image_size: tuple[int, int], row_slot: int) -> tuple[int, int, int, int]:
    """Approximate one visible Last War row in the normalized screenshot.

    Sentinel normalizes screenshots to 600x1064 by default.  The row geometry is
    intentionally approximate and padded; the character crop is refined inside
    the field box.
    """
    width, height = image_size
    scale_x = width / 600.0
    scale_y = height / 1064.0
    center_y = (170.0 + max(row_slot, 0) * 83.0) * scale_y
    top = int(max(105 * scale_y, center_y - 36 * scale_y))
    bottom = int(min(height, center_y + 42 * scale_y))
    return 0, top, width, bottom


def _field_box(image_size: tuple[int, int], row_slot: int, field: str, *, text_length: int, position: int) -> tuple[int, int, int, int]:
    width, height = image_size
    scale_x = width / 600.0
    _x0, y0, _x1, y1 = _ranking_row_box(image_size, row_slot)
    # Based on normalized Last War ranking layout: rank at ~55px, identity
    # column starts around 190px, power column around 455px.
    if field == "alliance_tag":
        # Tags are short and sit at the beginning of the identity column.
        left = 188 * scale_x
        right = 255 * scale_x
        total_chars = max(text_length, 2)
    else:
        left = 190 * scale_x
        right = 445 * scale_x
        total_chars = max(text_length, 1)

    char_width = max((right - left) / max(total_chars, 1), 5 * scale_x)
    cx = left + (min(max(position, 0), max(total_chars - 1, 0)) + 0.5) * char_width
    pad_x = max(10 * scale_x, char_width * 1.25)
    # Text baseline is usually in the upper half of the row; keep generous y pad.
    top = max(0, int(y0 + 4 * (height / 1064.0)))
    bottom = min(height, int(y1 - 10 * (height / 1064.0)))
    return (
        int(max(0, cx - pad_x)),
        int(top),
        int(min(width, cx + pad_x)),
        int(bottom),
    )


def _image_variants(image):
    if ImageOps is None or ImageEnhance is None or ImageFilter is None:
        return []
    base = image.convert("RGB")
    gray = ImageOps.grayscale(base)
    yield "gray_x6", gray.resize((gray.width * 6, gray.height * 6))
    yield "contrast_x6", ImageEnhance.Contrast(gray).enhance(2.2).resize((gray.width * 6, gray.height * 6))
    yield "sharp_x6", gray.filter(ImageFilter.SHARPEN).resize((gray.width * 6, gray.height * 6))
    inverted = ImageOps.invert(gray)
    yield "invert_x6", ImageEnhance.Contrast(inverted).enhance(2.0).resize((gray.width * 6, gray.height * 6))


def _read_variant(reader: Any, image) -> list[tuple[str, float]]:
    if reader is None:
        return []
    if hasattr(reader, "read_rows"):
        results = reader.read_rows(image)
    elif callable(reader):
        results = reader(image)
    else:
        return []
    values: list[tuple[str, float]] = []
    for result in results or []:
        try:
            _box, text, confidence = result
        except Exception:
            continue
        values.append((str(text or ""), float(confidence or 0.0)))
    return values


def _choose_character(text: str, target: ReOcrTarget) -> str:
    clean = str(text or "").strip()
    if not clean:
        return ""
    # Prefer explicit expected/observed occurrences in the OCR crop because the
    # crop is small but may still include brackets or nearby glyphs.
    for candidate in (target.expected, target.observed):
        if candidate and candidate in clean:
            return candidate
    if target.position < len(clean):
        return clean[target.position]
    return clean[0]


def _select_vote(votes: Iterable[CharacterVote]) -> tuple[str, float]:
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}
    for vote in votes:
        if not vote.char:
            continue
        totals[vote.char] = totals.get(vote.char, 0.0) + max(vote.confidence, 0.01)
        counts[vote.char] = counts.get(vote.char, 0) + 1
    if not totals:
        return "", 0.0
    selected = max(totals, key=lambda ch: (counts[ch], totals[ch]))
    confidence = min(1.0, totals[selected] / max(sum(totals.values()), 1e-9))
    return selected, round(confidence, 4)


def verify_target_from_screenshot(
    *,
    screenshot_path: Path,
    target: ReOcrTarget,
    expected_text: str,
    observed_text: str,
    row_slot: int | None,
    reader: Any = None,
) -> CharacterVerificationEvidence:
    """Re-read one target character from a screenshot crop.

    If no OCR reader is supplied or the crop cannot be read, the function still
    returns deterministic unresolved evidence.  It never guesses from historical
    identity context.
    """
    if Image is None:
        return CharacterVerificationEvidence(target.field, target.position, target.expected, target.observed, screenshot_path.name, row_slot, None, "unresolved", reason="pillow_unavailable")
    if row_slot is None:
        return CharacterVerificationEvidence(target.field, target.position, target.expected, target.observed, screenshot_path.name, row_slot, None, "unresolved", reason="missing_row_slot")
    if not screenshot_path.exists():
        return CharacterVerificationEvidence(target.field, target.position, target.expected, target.observed, screenshot_path.name, row_slot, None, "unresolved", reason="screenshot_missing")

    image = Image.open(screenshot_path)
    text_for_field = expected_text if target.expected else observed_text
    box = _field_box(image.size, row_slot, target.field, text_length=len(text_for_field or observed_text or target.observed or ""), position=target.position)
    crop = image.crop(box)
    votes: list[CharacterVote] = []
    for variant_name, variant_image in _image_variants(crop):
        for text, confidence in _read_variant(reader, variant_image):
            char = _choose_character(text, target)
            votes.append(CharacterVote(variant=variant_name, text=text, confidence=confidence, char=char))

    selected, confidence = _select_vote(votes)
    if selected and target.expected and selected == target.expected and confidence >= 0.55:
        status = "verified_expected"
    elif selected and target.observed and selected == target.observed and confidence >= 0.55:
        status = "verified_observed"
    elif selected:
        status = "ambiguous_vote"
    else:
        status = "unresolved"
    return CharacterVerificationEvidence(
        field=target.field,
        position=target.position,
        expected=target.expected,
        observed=target.observed,
        screenshot=screenshot_path.name,
        row_slot=row_slot,
        crop_box=box,
        status=status,
        selected=selected,
        confidence=confidence,
        votes=tuple(votes),
        reason="targeted_crop_reocr",
    )


def summarize_evidence(evidence: Iterable[CharacterVerificationEvidence]) -> dict[str, int]:
    items = list(evidence)
    return {
        "targets": len(items),
        "verified_expected": sum(1 for item in items if item.status == "verified_expected"),
        "verified_observed": sum(1 for item in items if item.status == "verified_observed"),
        "ambiguous": sum(1 for item in items if item.status == "ambiguous_vote"),
        "unresolved": sum(1 for item in items if item.status == "unresolved"),
    }
