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
import time
from pathlib import Path
from typing import Any, Callable, Iterable

try:
    import numpy as np
except Exception:  # pragma: no cover - import environment dependent
    np = None  # type: ignore

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
    crop_strategy: str = ""
    crop_candidate_index: int = 0
    crop_candidate_count: int = 1
    crop_candidate_reason: str = ""
    crop_anchor_status: str = ""
    crop_anchor_text: str = ""
    crop_diagnostic: str = ""
    text_length: int = 0
    expected_text: str = ""
    observed_text: str = ""
    allowed_chars: str = ""
    target_total_ms: float = 0.0
    crop_generation_ms: float = 0.0
    variant_build_ms: float = 0.0
    ocr_read_ms: float = 0.0
    vote_selection_ms: float = 0.0

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
    """Approximate one visible Last War row in a screenshot.

    The 551 Gold Fidelity debug run exposed an important geometry bug: some
    supplied screenshots are not normalized to Sentinel's 600x1064 baseline.
    They are visible-window captures around 627x915.  Applying the 1064-based
    row pitch to those images shifts crops upward by roughly one row; this is
    why a `[PbC]` target could read `[IVE]` from the neighbouring row.

    Keep the old normalized geometry for tall images, but use a window-capture
    geometry for short/wide screenshots.  This is still conservative evidence;
    it only changes where the validation crop looks, not Operational Truth.
    """
    width, height = image_size
    if width <= 0 or height <= 0:
        return 0, 0, width, height

    aspect = height / max(width, 1)
    if aspect < 1.60:
        # Observed 551 screenshots: 627x915, first row center near y=176 and
        # row pitch near 113px.  Scale both dimensions from that baseline.
        scale_y = height / 915.0
        center_y = (176.0 + max(row_slot, 0) * 113.0) * scale_y
        top = int(max(0, center_y - 48 * scale_y))
        bottom = int(min(height, center_y + 50 * scale_y))
        return 0, top, width, bottom

    # Normalized/importer geometry used by the original targeted ReOCR path.
    scale_y = height / 1064.0
    center_y = (170.0 + max(row_slot, 0) * 83.0) * scale_y
    top = int(max(105 * scale_y, center_y - 36 * scale_y))
    bottom = int(min(height, center_y + 42 * scale_y))
    return 0, top, width, bottom

def _field_box(image_size: tuple[int, int], row_slot: int, field: str, *, text_length: int, position: int, field_text: str = "") -> tuple[int, int, int, int]:
    width, height = image_size
    scale_x = width / 600.0
    _x0, y0, _x1, y1 = _ranking_row_box(image_size, row_slot)
    aspect = height / max(width, 1)

    if aspect < 1.60:
        # Visible-window screenshots have a slightly wider layout than the
        # 600x1064 normalized baseline.  Use coordinates measured from the 551
        # screen pack: identity text begins after the avatar around x=210.
        if field == "alliance_tag":
            # v0.9.5.105: keep the tag crop on the target glyph only.  The
            # .104 crop still included neighbouring tag characters and the
            # second line ("Warzone #551"), which made `[PbC]` position 1 vote
            # as CJK/noise instead of the middle `b`.  Use the measured 551
            # visible-window tag glyph centers and a narrow horizontal pad.
            tag_left = 198 * scale_x
            tag_right = 256 * scale_x
            visible_slots = max(text_length + 2, 5)  # [ + TAG + ]
            char_width = max((tag_right - tag_left) / visible_slots, 8 * scale_x)
            tag_pos = min(max(position + 1, 0), visible_slots - 1)
            cx = tag_left + (tag_pos + 0.5) * char_width
            pad_x = max(5 * scale_x, char_width * 0.45)
        else:
            # v0.9.5.105: late Latin-name targets such as Joncollins[2/1] were
            # mapped across the entire identity column, so position 10 landed
            # on the final `1` and position 11 landed on empty space.  For
            # Latin-only names use a glyph-pitch model anchored at the observed
            # start of the commander name; keep the wider field model for
            # mixed CJK/Hangul names where glyph widths vary heavily.
            raw_text = str(field_text or "")
            has_wide_script = any(ord(ch) > 127 for ch in raw_text)
            total_chars = max(text_length, 1)
            if not has_wide_script:
                left = 263 * scale_x
                char_width = max(10.8 * scale_x, 7 * scale_x)
                cx = left + (min(max(position, 0), max(total_chars - 1, 0)) + 0.5) * char_width
                pad_x = max(7 * scale_x, char_width * 0.65)
            else:
                left = 258 * scale_x
                right = 438 * scale_x
                char_width = max((right - left) / max(total_chars, 1), 7 * scale_x)
                cx = left + (min(max(position, 0), max(total_chars - 1, 0)) + 0.5) * char_width
                pad_x = max(12 * scale_x, char_width * 1.05)
            power_guard = 430 * scale_x
            cx = min(cx, power_guard - max(9 * scale_x, char_width * 0.55))
        # Focus on the commander/title line only.  v0.9.5.105 cropped too
        # low (y0+12), leaving only the lower half of orange glyphs such as
        # Joncollins21 and [PbC].  Start slightly above the title baseline
        # while still excluding the lower Warzone line.
        row_scale_y = height / 915.0
        top = max(0, int(y0 - 4 * row_scale_y))
        bottom = min(height, int(y0 + 45 * row_scale_y))
    else:
        # Based on normalized Last War ranking layout: rank at ~55px, identity
        # column starts around 190px, power column around 455px.
        if field == "alliance_tag":
            left = 188 * scale_x
            right = 260 * scale_x
            total_chars = max(text_length, 3)
            char_width = max((right - left) / max(total_chars + 2, 1), 7 * scale_x)
            cx = left + (min(max(position + 1, 0), max(total_chars + 1, 0)) + 0.5) * char_width
            pad_x = max(14 * scale_x, char_width * 1.8)
        else:
            left = 258 * scale_x
            right = 448 * scale_x
            total_chars = max(text_length, 1)
            char_width = max((right - left) / max(total_chars, 1), 6 * scale_x)
            cx = left + (min(max(position, 0), max(total_chars - 1, 0)) + 0.5) * char_width
            pad_x = max(12 * scale_x, char_width * 1.5)
        top = max(0, int(y0 + 4 * (height / 1064.0)))
        bottom = min(height, int(y1 - 10 * (height / 1064.0)))

    return (
        int(max(0, cx - pad_x)),
        int(top),
        int(min(width, cx + pad_x)),
        int(bottom),
    )


def _clamped_box(
    *,
    width: int,
    height: int,
    cx: float,
    cy: float,
    bw: float,
    bh: float,
) -> tuple[int, int, int, int]:
    return (
        int(max(0, round(cx - bw / 2))),
        int(max(0, round(cy - bh / 2))),
        int(min(width, round(cx + bw / 2))),
        int(min(height, round(cy + bh / 2))),
    )


def _alliance_tag_block_candidates(
    base_box: tuple[int, int, int, int],
    image_size: tuple[int, int],
    target: ReOcrTarget,
) -> list[tuple[tuple[int, int, int, int], str]]:
    """Build full-tag block crops from a target glyph crop.

    v0.9.5.109 showed the remaining PbC/PBC blocker clearly: the middle `b`
    often looked like h/6/CJK noise when cropped as a single glyph.  The safer
    approach is to first let OCR see the complete short tag block (`[PbC]` or
    `PbC`) and only then pick the requested glyph position from that block.

    This function derives a block crop from the target glyph center instead of
    hard-coding a specific server/alliance.  It remains screenshot-local and
    does not use historical identity knowledge.
    """
    width, height = image_size
    x0, y0, x1, y1 = base_box
    bw = max(1, x1 - x0)
    bh = max(1, y1 - y0)
    glyph_cx = (x0 + x1) / 2.0
    glyph_cy = (y0 + y1) / 2.0

    tag_len = max(len(str(target.expected or target.observed or "")), 3)
    visible_slots = tag_len + 2  # opening bracket + tag + closing bracket
    target_slot = min(max(target.position + 1, 0), visible_slots - 1)

    # A single-glyph crop is padded, so its width is larger than the real glyph
    # pitch.  0.72 approximates the visual pitch in the 551 window screenshots.
    glyph_step = max(8.0, bw * 0.72)
    block_center = glyph_cx + (((visible_slots - 1) / 2.0) - target_slot) * glyph_step
    block_width = max(visible_slots * glyph_step + 14.0, bw * 3.8)
    block_height = min(max(bh * 1.04, bh + 2), bh * 1.28)

    candidates = [
        (_clamped_box(width=width, height=height, cx=block_center, cy=glyph_cy, bw=block_width, bh=block_height), "tag_block_anchor"),
        (_clamped_box(width=width, height=height, cx=block_center, cy=glyph_cy - bh * 0.16, bw=block_width * 1.08, bh=block_height * 1.08), "tag_block_up_anchor"),
        (_clamped_box(width=width, height=height, cx=block_center - glyph_step * 0.35, cy=glyph_cy, bw=block_width * 1.10, bh=block_height), "tag_block_left_anchor"),
        (_clamped_box(width=width, height=height, cx=block_center + glyph_step * 0.35, cy=glyph_cy, bw=block_width * 1.10, bh=block_height), "tag_block_right_anchor"),
    ]
    return [(box, reason) for box, reason in candidates if box[2] > box[0] and box[3] > box[1]]


def _crop_box_variants(base_box: tuple[int, int, int, int], image_size: tuple[int, int], target: ReOcrTarget) -> list[tuple[tuple[int, int, int, int], str]]:
    """Return conservative calibration candidates around the primary crop.

    v0.9.5.110 adds a tag-block anchor path before glyph probes.  It does not
    guess a tag from history.  It simply gives OCR the full short tag first,
    because case-sensitive tags such as `[PbC]` are easier to read as a block
    than as a single middle glyph.
    """
    width, height = image_size
    x0, y0, x1, y1 = base_box
    bw = max(1, x1 - x0)
    bh = max(1, y1 - y0)

    variants: list[tuple[tuple[int, int, int, int], str]] = []
    seen: set[tuple[int, int, int, int]] = set()

    def add(box: tuple[int, int, int, int], reason: str) -> None:
        if box[2] <= box[0] or box[3] <= box[1] or box in seen:
            return
        seen.add(box)
        variants.append((box, reason))

    if target.field == "alliance_tag":
        # Try full tag anchors first so `[PbC]` can be read positionally before
        # the verifier falls back to noisy single-glyph crops.
        for box, reason in _alliance_tag_block_candidates(base_box, image_size, target):
            add(box, reason)
        specs = [
            (0.0, 0.0, 1.0, "base"),
            (-0.65, 0.0, 1.30, "left_probe"),
            (0.65, 0.0, 1.30, "right_probe"),
            (-0.35, -0.18, 1.45, "left_up_probe"),
            (0.35, -0.18, 1.45, "right_up_probe"),
            (0.0, -0.18, 1.25, "up_wide"),
            (-1.00, 0.0, 3.25, "legacy_full_tag_wide"),
            (-1.00, -0.18, 3.45, "legacy_full_tag_up_wide"),
        ]
    else:
        specs = [
            (0.0, 0.0, 1.0, "base"),
            (-0.50, 0.0, 1.65, "left_wide"),
            (0.50, 0.0, 1.65, "right_wide"),
            (0.0, -0.18, 1.45, "up_wide"),
            (-0.35, -0.18, 1.90, "left_up_wide"),
            (0.35, -0.18, 1.90, "right_up_wide"),
        ]

    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    for dx_factor, dy_factor, scale, reason in specs:
        nw = max(bw * scale, bw + 2)
        nh = max(bh * min(scale, 1.25), bh)
        ncx = cx + dx_factor * bw
        ncy = cy + dy_factor * bh
        add(_clamped_box(width=width, height=height, cx=ncx, cy=ncy, bw=nw, bh=nh), reason)
    return variants



def is_local_glyph_target(target: ReOcrTarget, *, expected_text: str = "", observed_text: str = "") -> bool:
    """Return True when a target is safe and useful for local glyph re-OCR.

    v0.9.5.109 narrows Character ReOCR to the problem it can actually solve:
    a small ambiguous glyph in an otherwise aligned identity.  It must not run
    expensive OCR for broad display drift such as a Hangul name being read as
    CJK, or an UNKNOWN row expanding into many synthetic target positions.  Those
    cases remain DataGuard blockers / context gaps, not local glyph fixes.
    """
    field = str(target.field or "")
    expected = str(target.expected or "")
    observed = str(target.observed or "")
    group = str(target.group or "")
    reason = str(target.reason or "")

    if field == "alliance_tag":
        # Tags are short and strategically important.  Re-read case, missing,
        # and confusable differences, but only while we still have a plausible
        # tag field rather than an entire missing row.
        if not expected and not observed:
            return False
        if len(str(expected_text or "")) > 5 or len(str(observed_text or "")) > 5:
            return False
        return True

    if field != "player_name":
        return False

    # A local glyph verifier normally needs at least one visible target glyph.
    # v0.9.5.115 adds one narrow exception: Latin-only names with one/few
    # missing expected glyphs, e.g. Mizzenmast -> Mzzenmast or Drpeek -> Ieek.
    # This remains screenshot-local and explicitly excludes mixed CJK/Hangul
    # display drift.
    if not expected or not observed:
        if expected and not observed and _safe_latin_gap_pair(expected_text, observed_text):
            return expected.isascii() and (expected.isalnum() or expected.isspace())
        return False

    # Primary target: classical OCR confusion families such as 2/z or 1/l.
    if group:
        return True

    # Secondary target: same ASCII letter with different case.  This matters for
    # player names too, but we keep it limited to one glyph and avoid general
    # Unicode replacement attempts.
    if len(expected) == len(observed) == 1 and expected.isascii() and observed.isascii():
        if expected.lower() == observed.lower() and expected != observed:
            return True

    return False


def filter_local_glyph_targets(targets: Iterable[ReOcrTarget], *, expected_name: str = "", observed_name: str = "", expected_alliance: str = "", observed_alliance: str = "") -> list[ReOcrTarget]:
    """Filter a target plan to local glyph-verification work only."""
    filtered: list[ReOcrTarget] = []
    seen: set[tuple[str, int, str, str, str]] = set()
    for target in targets:
        expected_text = expected_name if target.field == "player_name" else expected_alliance
        observed_text = observed_name if target.field == "player_name" else observed_alliance
        if not is_local_glyph_target(target, expected_text=expected_text, observed_text=observed_text):
            continue
        key = (target.field, target.position, target.expected, target.observed, target.group)
        if key in seen:
            continue
        seen.add(key)
        filtered.append(target)
    return filtered


def _is_ascii_latinish(text: str) -> bool:
    text = str(text or "")
    if not text:
        return False
    # Permit player-name punctuation/spacing that occurs in Latin Last War names,
    # but reject CJK/Hangul/Kana drift.  This keeps the first-contact OCR path
    # screenshot-local while allowing missing Latin glyphs such as Mizzenmast ->
    # Mzzenmast to be verified instead of being skipped as nonlocal.
    return all(ord(ch) < 128 for ch in text)


def _compact_latin_identity(text: str) -> str:
    return "".join(ch.lower() for ch in str(text or "") if ch.isalnum())


def _safe_latin_gap_pair(expected_text: str, observed_text: str) -> bool:
    if not (_is_ascii_latinish(expected_text) and _is_ascii_latinish(observed_text)):
        return False
    expected_key = _compact_latin_identity(expected_text)
    observed_key = _compact_latin_identity(observed_text)
    if not expected_key or not observed_key:
        return False
    # A local gap verifier is intended for one/few missing glyphs in an otherwise
    # aligned Latin name, not for broad substitutions or OCR garbage suffixes.
    if abs(len(expected_key) - len(observed_key)) > 3:
        return False
    # Deletion-style cases: Mizzenmast/Mzzenmast, Drpeek/Ieek, N E R D/NER0.
    # Do not require containment only; a trailing confusable may still need its
    # own glyph vote.
    from difflib import SequenceMatcher
    return SequenceMatcher(a=expected_key, b=observed_key).ratio() >= 0.72

def _status_rank(status: str) -> int:
    return {"verified_expected": 400, "verified_observed": 300, "ambiguous_vote": 200, "unresolved": 0}.get(status, 0)


def _diagnostic_rank(diagnostic: str) -> int:
    return {"crop_anchor_ok": 60, "vote_outside_allowed_set": 30, "crop_field_mismatch": 10, "crop_power_column_bleed": 8, "crop_no_text_detected": 0}.get(diagnostic, 0)


def _evidence_rank(evidence: CharacterVerificationEvidence) -> tuple[int, int, int, float]:
    nonempty = sum(1 for vote in evidence.votes if vote.text)
    chars = sum(1 for vote in evidence.votes if vote.char)
    return (_status_rank(evidence.status), _diagnostic_rank(evidence.crop_diagnostic), chars + nonempty, evidence.confidence)


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


def _to_ocr_input(image):
    """Convert PIL crops into an OCR-provider compatible input.

    EasyOCR accepts paths, bytes, or numpy arrays.  The targeted re-OCR
    variants are PIL images, so passing them through directly raises
    ValueError.  Keep this conversion local so fake readers in tests can still
    receive image-like objects when numpy is unavailable.
    """
    if np is not None and Image is not None and isinstance(image, Image.Image):
        return np.asarray(image.convert("RGB"))
    return image


def _read_variant(reader: Any, image) -> list[tuple[str, float]]:
    if reader is None:
        return []
    ocr_input = _to_ocr_input(image)
    if hasattr(reader, "read_rows"):
        results = reader.read_rows(ocr_input)
    elif callable(reader):
        results = reader(ocr_input)
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


def _allowed_target_chars(target: ReOcrTarget) -> set[str]:
    allowed = {ch for ch in (target.expected, target.observed) if ch}
    allowed.update(ch for ch in str(target.group or "") if ch)
    return allowed


def _tag_content(text: str) -> str:
    clean = str(text or "").strip()
    if "[" in clean and "]" in clean and clean.index("[") < clean.rindex("]"):
        return clean[clean.index("[") + 1:clean.rindex("]")]
    if clean.startswith("["):
        return clean[1:]
    return clean


def _choose_character(text: str, target: ReOcrTarget) -> str:
    clean = str(text or "").strip()
    if not clean:
        return ""

    allowed = _allowed_target_chars(target)

    # Alliance tags are position-sensitive and short.  For text like [PbC], the
    # target at position 1 is b, not the first visible character P.  This fixes
    # the .100 false vote pattern where [PbC]/[PC] repeatedly selected P.
    if target.field == "alliance_tag":
        tag = _tag_content(clean)
        if 0 <= target.position < len(tag):
            ch = tag[target.position]
            if not allowed or ch in allowed:
                return ch
        for ch in tag:
            if ch in allowed:
                return ch
        return ""

    # For player names, prefer exact target/confusion glyphs when the crop sees
    # them.  If no allowed glyph appears, return an empty vote instead of a
    # random neighbouring bracket/CJK glyph; that keeps ReOCR conservative.
    for candidate in (target.expected, target.observed):
        if candidate and candidate in clean:
            return candidate
    for ch in clean:
        if ch in allowed:
            return ch
    if allowed:
        return ""
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


def _text_contains_anchor(text: str, expected_text: str, observed_text: str, field: str) -> bool:
    clean = str(text or "")
    if not clean:
        return False
    if field == "alliance_tag":
        anchors = [_tag_content(expected_text), _tag_content(observed_text), expected_text, observed_text]
    else:
        anchors = [expected_text, observed_text]
        # A short Latin core is enough for diagnostics without accepting it as a
        # verified character vote.
        for value in (expected_text, observed_text):
            latin = "".join(ch for ch in str(value) if ch.isascii() and (ch.isalnum() or ch.isspace())).strip()
            if len(latin) >= 4:
                anchors.append(latin)
    return any(anchor and str(anchor) in clean for anchor in anchors)


def _classify_crop_anchor(votes: list[CharacterVote], target: ReOcrTarget, expected_text: str, observed_text: str) -> tuple[str, str, str]:
    """Classify whether OCR text appears to come from the intended row/field.

    This is diagnostic only. It does not turn an OCR vote into Operational Truth.
    It helps distinguish a genuine `no_votes` character miss from a row-slot or
    field-anchor error such as `[PbC]` crops reading `[IVE]`.
    """
    texts = [vote.text for vote in votes if vote.text]
    if not texts:
        return "no_text", "", "crop_no_text_detected"
    joined = " | ".join(texts)
    if any(_text_contains_anchor(text, expected_text, observed_text, target.field) for text in texts):
        return "anchor_seen", joined, "crop_anchor_ok"
    if target.field == "alliance_tag":
        bracketed = [_tag_content(text) for text in texts if "[" in text or "]" in text]
        if bracketed:
            return "field_mismatch", joined, "crop_field_mismatch"
    else:
        # When a player-name crop returns mostly power-like digits (e.g.
        # 286/320/264) the problem is not character classification; the crop
        # leaked into the power column.  Keep this as diagnostics so the next
        # sprint can quantify geometry rather than blaming OCR.
        compact = "".join(ch for ch in joined if ch.isalnum() or ch in ",.")
        digit_count = sum(ch.isdigit() for ch in compact)
        if compact and digit_count >= max(2, int(len(compact) * 0.65)):
            return "field_mismatch", joined, "crop_power_column_bleed"
    return "text_without_anchor", joined, "vote_outside_allowed_set"


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
    total_start = time.perf_counter()
    # Pure spacing gaps in otherwise Latin names are not OCR-readable glyphs.
    # Treat them as verified formatting gaps only after the local-glyph gate has
    # proven the pair is safe Latin text.  This prevents spaces from blocking
    # Core Identity while still leaving non-Latin drift conservative.
    if target.field == "player_name" and target.expected == " " and not target.observed and _safe_latin_gap_pair(expected_text, observed_text):
        elapsed = (time.perf_counter() - total_start) * 1000.0
        return CharacterVerificationEvidence(
            target.field, target.position, target.expected, target.observed, screenshot_path.name, row_slot, None,
            "verified_expected", selected=" ", confidence=1.0, reason="latin_spacing_gap",
            text_length=len(expected_text or observed_text or ""), expected_text=expected_text, observed_text=observed_text,
            allowed_chars=" ", target_total_ms=elapsed,
        )
    if Image is None:
        return CharacterVerificationEvidence(target.field, target.position, target.expected, target.observed, screenshot_path.name, row_slot, None, "unresolved", reason="pillow_unavailable", expected_text=expected_text, observed_text=observed_text)
    if row_slot is None:
        return CharacterVerificationEvidence(target.field, target.position, target.expected, target.observed, screenshot_path.name, row_slot, None, "unresolved", reason="missing_row_slot", expected_text=expected_text, observed_text=observed_text)
    if not screenshot_path.exists():
        return CharacterVerificationEvidence(target.field, target.position, target.expected, target.observed, screenshot_path.name, row_slot, None, "unresolved", reason="screenshot_missing", expected_text=expected_text, observed_text=observed_text)

    image = Image.open(screenshot_path)
    text_for_field = expected_text if target.expected else observed_text
    text_length = len(text_for_field or observed_text or target.observed or "")
    crop_start = time.perf_counter()
    base_box = _field_box(image.size, row_slot, target.field, text_length=text_length, position=target.position, field_text=(text_for_field or observed_text or ""))
    candidate_boxes = _crop_box_variants(base_box, image.size, target)
    crop_generation_ms = (time.perf_counter() - crop_start) * 1000.0
    allowed = _allowed_target_chars(target)

    best: CharacterVerificationEvidence | None = None
    candidate_count = len(candidate_boxes)
    for candidate_index, (box, candidate_reason) in enumerate(candidate_boxes):
        candidate_start = time.perf_counter()
        crop = image.crop(box)
        votes: list[CharacterVote] = []
        variant_build_ms = 0.0
        ocr_read_ms = 0.0
        variants_start = time.perf_counter()
        variants = list(_image_variants(crop))
        variant_build_ms += (time.perf_counter() - variants_start) * 1000.0
        for variant_name, variant_image in variants:
            read_start = time.perf_counter()
            read_values = _read_variant(reader, variant_image)
            ocr_read_ms += (time.perf_counter() - read_start) * 1000.0
            for text, confidence in read_values:
                char = _choose_character(text, target)
                votes.append(CharacterVote(variant=variant_name, text=text, confidence=confidence, char=char))

        vote_start = time.perf_counter()
        selected, confidence = _select_vote(votes)
        crop_anchor_status, crop_anchor_text, crop_diagnostic = _classify_crop_anchor(votes, target, expected_text, observed_text)
        vote_selection_ms = (time.perf_counter() - vote_start) * 1000.0
        # Only accept a vote that is either the expected glyph, the observed glyph,
        # or an explicitly configured confusion-family member. Everything else is
        # unresolved noise, not evidence.
        if selected and allowed and selected not in allowed:
            selected = ""
            confidence = 0.0

        if selected and target.expected and selected == target.expected and confidence >= 0.55:
            status = "verified_expected"
        elif selected and target.observed and selected == target.observed and confidence >= 0.55:
            status = "verified_observed"
        elif selected:
            status = "ambiguous_vote"
        else:
            status = "unresolved"

        evidence = CharacterVerificationEvidence(
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
            crop_strategy="alliance_tag_position" if target.field == "alliance_tag" else "player_name_after_tag",
            crop_candidate_index=candidate_index,
            crop_candidate_count=candidate_count,
            crop_candidate_reason=candidate_reason,
            crop_anchor_status=crop_anchor_status,
            crop_anchor_text=crop_anchor_text,
            crop_diagnostic=crop_diagnostic,
            text_length=text_length,
            expected_text=expected_text,
            observed_text=observed_text,
            allowed_chars="".join(sorted(allowed)),
            target_total_ms=round((time.perf_counter() - total_start) * 1000.0, 3),
            crop_generation_ms=round(crop_generation_ms, 3),
            variant_build_ms=round(variant_build_ms, 3),
            ocr_read_ms=round(ocr_read_ms, 3),
            vote_selection_ms=round(vote_selection_ms, 3),
        )
        if best is None or _evidence_rank(evidence) > _evidence_rank(best):
            best = evidence
        # Expected-character evidence is the best possible outcome. Avoid extra
        # OCR calls once we have it.
        if evidence.status == "verified_expected" and evidence.confidence >= 0.55:
            break

    if best is not None:
        return best
    return CharacterVerificationEvidence(
        target.field, target.position, target.expected, target.observed, screenshot_path.name, row_slot, base_box, "unresolved",
        reason="no_crop_candidates",
        expected_text=expected_text,
        observed_text=observed_text,
        text_length=text_length,
        allowed_chars="".join(sorted(allowed)),
        target_total_ms=round((time.perf_counter() - total_start) * 1000.0, 3),
        crop_generation_ms=round(crop_generation_ms, 3),
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
