"""Adaptive Review OCR pipeline.

The primary import path must stay fast and conservative.  This module runs only
for rows that Sentinel already isolated for review/quarantine.  It creates
source-local row crops, applies deterministic image variants, reruns OCR, and
promotes a row back to Operational Truth only when the second pass produces
strictly better intrinsic evidence.

The pipeline deliberately does not use filename order, upload order, or neighbour
screenshots as truth.  It uses only the quarantined row, its source screenshot,
and the OCR evidence read from enhanced crops of that same visual row.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2

from parser.image import load_and_normalize_image
from parser.ranking import parse_ranking_rows

QUARANTINE_KEY = ("REVIEW", "ranking_guard_quarantine")


@dataclass(frozen=True)
class ReviewOcrVariant:
    name: str
    image: Any
    y_offset: int


def _safe_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float:
    try:
        if value is None or value == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _power(row: dict[str, Any]) -> int | None:
    return _safe_int(row.get("power") or row.get("hero_power") or row.get("alliance_power"))


def _row_y(row: dict[str, Any]) -> int | None:
    return _safe_int(row.get("visual_y") or row.get("y") or row.get("row_y"))


def _source_file(row: dict[str, Any]) -> str:
    return str(row.get("source_file") or "")


def _target_group(row: dict[str, Any]) -> tuple[int, str] | None:
    server = _safe_int(row.get("original_server") or row.get("server"))
    ranking_type = str(row.get("original_ranking_type") or row.get("expected_ranking_type") or row.get("ranking_type") or "")
    if server is None or ranking_type not in {"total_hero_power", "alliance_power"}:
        return None
    return server, ranking_type


def _normal_power_for_type(power: int | None, ranking_type: str) -> bool:
    if power is None:
        return False
    if ranking_type == "total_hero_power":
        return 80_000_000 <= power <= 500_000_000
    if ranking_type == "alliance_power":
        return 1_000_000_000 <= power <= 45_000_000_000
    return False


def _enhance_clahe(image):
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced_l = clahe.apply(l_channel)
    merged = cv2.merge((enhanced_l, a_channel, b_channel))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


def _sharpen(image):
    blurred = cv2.GaussianBlur(image, (0, 0), 1.0)
    return cv2.addWeighted(image, 1.55, blurred, -0.55, 0)


def build_review_ocr_variants(image, row: dict[str, Any], *, max_variants: int = 6) -> list[ReviewOcrVariant]:
    """Build deterministic row crop variants for a quarantined row."""
    y = _row_y(row)
    if y is None:
        return []

    height, width = image.shape[:2]
    variants: list[ReviewOcrVariant] = []
    crop_specs = [
        ("row_crop", 46, 0),
        ("row_crop_tall", 64, 0),
        ("row_crop_up", 56, -8),
        ("row_crop_down", 56, 8),
    ]

    for name, crop_height, shift in crop_specs:
        center = max(0, min(height - 1, int(y + shift)))
        top = max(0, center - crop_height // 2)
        bottom = min(height, center + crop_height // 2)
        if bottom - top < 18:
            continue
        crop = image[top:bottom, 0:width]
        variants.append(ReviewOcrVariant(name=name, image=crop, y_offset=top))

        upscaled = cv2.resize(crop, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        variants.append(ReviewOcrVariant(name=f"{name}_2x", image=upscaled, y_offset=top))

    # Add image-quality variants only after the plain crops.  This ordering makes
    # tests and reports deterministic.
    enriched: list[ReviewOcrVariant] = []
    for variant in variants[:2]:
        enriched.append(ReviewOcrVariant(name=f"{variant.name}_clahe", image=_enhance_clahe(variant.image), y_offset=variant.y_offset))
        enriched.append(ReviewOcrVariant(name=f"{variant.name}_sharpen", image=_sharpen(variant.image), y_offset=variant.y_offset))

    # Always include at least one enhancement variant when a caller asks for a
    # review bundle large enough for it.
    if max_variants >= 3 and enriched:
        ordered = variants[:2] + enriched + variants[2:]
    else:
        ordered = variants + enriched
    return ordered[:max_variants]


def _candidate_score(candidate: dict[str, Any], source_row: dict[str, Any], ranking_type: str) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    power = _power(candidate)
    original = _power(source_row)
    if _normal_power_for_type(power, ranking_type):
        score += 0.45
        reasons.append("normal_power_range")
    if original and power and abs(power - original) / max(original, 1) > 0.25:
        score += 0.10
        reasons.append("power_changed_materially")
    confidence = _safe_float(candidate.get("confidence"))
    score += min(0.20, confidence * 0.20)
    if str(candidate.get("name") or "").strip():
        score += 0.15
        reasons.append("name_present")
    if candidate.get("ocr_rank") is not None:
        score += 0.05
        reasons.append("rank_present")
    if ranking_type == "total_hero_power" and str(candidate.get("name") or "").strip().startswith("["):
        score += 0.05
        reasons.append("player_tag_shape")
    return round(score, 6), reasons


def _best_variant_candidate(reader: Any, variant: ReviewOcrVariant, row: dict[str, Any], ranking_type: str) -> dict[str, Any] | None:
    try:
        ocr = reader.read_rows(variant.image)
    except Exception as exc:  # pragma: no cover - provider failures are runtime-specific
        return {
            "review_ocr_variant": variant.name,
            "review_ocr_error": str(exc),
            "review_ocr_score": 0.0,
            "review_ocr_reasons": ["ocr_provider_error"],
        }
    parsed = parse_ranking_rows(ocr)
    if not parsed:
        return None
    scored: list[tuple[float, dict[str, Any], list[str]]] = []
    for candidate in parsed:
        score, reasons = _candidate_score(candidate, row, ranking_type)
        scored.append((score, candidate, reasons))
    scored.sort(key=lambda item: item[0], reverse=True)
    score, candidate, reasons = scored[0]
    return {
        "review_ocr_variant": variant.name,
        "review_ocr_score": score,
        "review_ocr_reasons": reasons,
        "candidate": candidate,
        "ocr_elements": len(ocr),
        "parsed_rows": len(parsed),
    }


def _promote_candidate(row: dict[str, Any], candidate_result: dict[str, Any], *, ranking_type: str) -> dict[str, Any] | None:
    candidate = candidate_result.get("candidate") or {}
    power = _power(candidate)
    if not _normal_power_for_type(power, ranking_type):
        return None
    if candidate_result.get("review_ocr_score", 0.0) < 0.62:
        return None

    promoted = dict(row)
    promoted["power_original"] = _power(row)
    promoted["power_recovered_from"] = _power(row)
    promoted["power"] = power
    if ranking_type == "total_hero_power":
        promoted["hero_power"] = power
    elif ranking_type == "alliance_power":
        promoted["alliance_power"] = power
    if candidate.get("name"):
        promoted["name"] = candidate.get("name")
    if candidate.get("ocr_rank") is not None:
        promoted["ocr_rank"] = candidate.get("ocr_rank")
    promoted["rank"] = promoted.get("rank") or promoted.get("computed_rank") or candidate.get("ocr_rank")
    promoted["ranking_type"] = ranking_type
    promoted["review_ocr_attempted"] = True
    promoted["review_ocr_status"] = "promoted"
    promoted["review_ocr_best_variant"] = candidate_result.get("review_ocr_variant")
    promoted["review_ocr_score"] = round(float(candidate_result.get("review_ocr_score") or 0.0), 4)
    promoted["review_ocr_decision"] = "promoted_after_adaptive_review_ocr"
    promoted["review_ocr_reasons"] = ";".join(candidate_result.get("review_ocr_reasons") or [])
    promoted["power_recovery_method"] = f"{ranking_type}_adaptive_review_ocr"
    promoted["power_recovery_status"] = "review_ocr_promoted"
    promoted["power_sanity_status"] = "review_ocr_promoted"
    promoted["power_sanity_confidence"] = promoted["review_ocr_score"]
    warning = str(promoted.get("ranking_guard_warning") or "").strip()
    suffix = "review_ocr:promoted_from_quarantine"
    promoted["ranking_guard_warning"] = suffix if not warning else f"{warning};{suffix}"
    return promoted


def annotate_review_ocr_skipped(row: dict[str, Any], reason: str) -> dict[str, Any]:
    annotated = dict(row)
    annotated["review_ocr_attempted"] = False
    annotated["review_ocr_status"] = "skipped"
    annotated["review_ocr_decision"] = reason
    return annotated


def run_adaptive_review_ocr(
    grouped: dict[tuple[Any, str], list[dict[str, Any]]],
    *,
    reader: Any,
    screenshot_dir: Path,
    target_width: int,
    target_height: int,
    enabled: bool = True,
    max_variants_per_row: int = 6,
) -> dict[tuple[Any, str], list[dict[str, Any]]]:
    """Run adaptive second-pass OCR for quarantined ranking rows.

    The function returns a new grouped mapping.  It promotes only rows with clear
    second-pass evidence; all other rows remain in quarantine with review OCR
    metadata explaining what was attempted or why it was skipped.
    """
    quarantine_rows = list(grouped.get(QUARANTINE_KEY, []))
    if not quarantine_rows:
        return grouped

    result: dict[tuple[Any, str], list[dict[str, Any]]] = {
        key: list(rows) for key, rows in grouped.items() if key != QUARANTINE_KEY
    }
    remaining: list[dict[str, Any]] = []
    image_cache: dict[str, Any] = {}

    for row in quarantine_rows:
        target = _target_group(row)
        if not enabled:
            remaining.append(annotate_review_ocr_skipped(row, "review_ocr_disabled"))
            continue
        if target is None:
            remaining.append(annotate_review_ocr_skipped(row, "missing_target_group"))
            continue
        source_file = _source_file(row)
        if not source_file:
            remaining.append(annotate_review_ocr_skipped(row, "missing_source_file"))
            continue
        if _row_y(row) is None:
            remaining.append(annotate_review_ocr_skipped(row, "missing_row_y"))
            continue
        image_path = screenshot_dir / source_file
        if not image_path.exists():
            remaining.append(annotate_review_ocr_skipped(row, "source_image_not_found"))
            continue

        if source_file not in image_cache:
            image_cache[source_file] = load_and_normalize_image(image_path, target_width, target_height)
        variants = build_review_ocr_variants(image_cache[source_file], row, max_variants=max_variants_per_row)
        if not variants:
            remaining.append(annotate_review_ocr_skipped(row, "no_review_ocr_variants"))
            continue

        variant_results = [
            candidate_result
            for variant in variants
            if (candidate_result := _best_variant_candidate(reader, variant, row, target[1])) is not None
        ]
        variant_results.sort(key=lambda item: float(item.get("review_ocr_score") or 0.0), reverse=True)
        best = variant_results[0] if variant_results else None
        promoted = _promote_candidate(row, best, ranking_type=target[1]) if best else None
        if promoted is not None:
            promoted["review_ocr_variants"] = len(variants)
            promoted["review_ocr_candidate_count"] = len(variant_results)
            result.setdefault(target, []).append(promoted)
            continue

        annotated = dict(row)
        annotated["review_ocr_attempted"] = True
        annotated["review_ocr_status"] = "no_promotion"
        annotated["review_ocr_variants"] = len(variants)
        annotated["review_ocr_candidate_count"] = len(variant_results)
        if best:
            annotated["review_ocr_best_variant"] = best.get("review_ocr_variant")
            annotated["review_ocr_score"] = round(float(best.get("review_ocr_score") or 0.0), 4)
            annotated["review_ocr_reasons"] = ";".join(best.get("review_ocr_reasons") or [])
        annotated["review_ocr_decision"] = "kept_in_quarantine_after_review_ocr"
        remaining.append(annotated)

    if remaining:
        result.setdefault(QUARANTINE_KEY, []).extend(remaining)
    return result
