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


def _digit_preservation_score(observed: int, candidate: int) -> float:
    source = str(observed)
    target = str(candidate)
    if not source or not target:
        return 0.0
    prefix = 0
    for left, right in zip(source, target):
        if left != right:
            break
        prefix += 1
    suffix = 0
    for left, right in zip(reversed(source), reversed(target)):
        if left != right:
            break
        suffix += 1
    cursor = 0
    matched = 0
    for digit in target:
        if cursor < len(source) and digit == source[cursor]:
            cursor += 1
            matched += 1
    subsequence = matched / max(len(source), 1)
    score = (0.48 * (prefix / max(len(source), 1))) + (0.32 * (suffix / max(len(source), 1))) + (0.20 * subsequence)
    if target.startswith(source):
        score += 0.16
    if target.startswith(source[:3]) and target.endswith(source[-4:]):
        score += 0.14
    if len(target) == len(source) + 1 and target.replace("0", "", 1) == source:
        score += 0.08
    return round(min(1.0, max(0.0, score)), 6)


def _low_truncation_candidates(observed: int) -> list[dict[str, Any]]:
    values: dict[int, str] = {}
    if not (1_000_000 <= observed < 50_000_000):
        return []
    text = str(observed)
    for multiplier, method in ((10, "scale_x10_truncated_digit"), (100, "scale_x100_truncated_digit")):
        candidate = observed * multiplier
        if 80_000_000 <= candidate <= 500_000_000:
            values[candidate] = method
    for index in range(1, len(text)):
        candidate = int(text[:index] + "0" + text[index:])
        if 80_000_000 <= candidate <= 500_000_000:
            values.setdefault(candidate, "insert_zero")
    return [
        {
            "value": value,
            "method": method,
            "digit_preservation_score": _digit_preservation_score(observed, value),
        }
        for value, method in sorted(values.items())
    ]


def _normal_source_rows(rows: list[dict[str, Any]], source_file: str, ranking_type: str) -> list[dict[str, Any]]:
    normal: list[dict[str, Any]] = []
    for row in rows:
        if _source_file(row) != source_file:
            continue
        power = _power(row)
        if _normal_power_for_type(power, ranking_type):
            normal.append(row)
    return normal


def _safe_rank_value(value: Any) -> int | None:
    return _safe_int(value)


def _rank_for_insert(sorted_powers: list[int], candidate: int) -> tuple[int | None, int | None, int]:
    higher = [power for power in sorted_powers if power >= candidate]
    lower = [power for power in sorted_powers if power <= candidate]
    previous_power = min(higher) if higher else None
    next_power = max(lower) if lower else None
    reconstructed_rank = len([power for power in sorted_powers if power > candidate]) + 1
    return previous_power, next_power, reconstructed_rank


def _candidate_duplicate(candidate: int, target_rows: list[dict[str, Any]]) -> bool:
    for row in target_rows:
        power = _power(row)
        if power is None:
            continue
        if abs(power - candidate) <= max(50_000, int(candidate * 0.00035)):
            return True
    return False


def _contextual_score(candidate: dict[str, Any], row: dict[str, Any], *, target_rows: list[dict[str, Any]], source_rows: list[dict[str, Any]], ranking_type: str) -> tuple[float, list[str], dict[str, Any]]:
    value = int(candidate["value"])
    if not _normal_power_for_type(value, ranking_type):
        return 0.0, ["candidate_out_of_range"], {}
    if ranking_type != "total_hero_power":
        return 0.0, ["contextual_reconstruction_only_for_thp"], {}

    source_powers = sorted([power for source_row in source_rows if (power := _power(source_row)) is not None], reverse=True)
    previous_power, next_power, reconstructed_rank = _rank_for_insert(source_powers, value)
    digit = float(candidate.get("digit_preservation_score") or 0.0)
    score = 0.0
    reasons: list[str] = []

    if previous_power is not None and next_power is not None:
        score += 0.35
        reasons.append("bounded_by_source_anchors")
        gap = max(previous_power - next_power, 1)
        if previous_power >= value >= next_power:
            score += 0.25
            reasons.append("fits_anchor_power_gap")
        distance = min(abs(previous_power - value), abs(value - next_power)) / max(gap, 1)
        if distance <= 0.40:
            score += 0.08
            reasons.append("near_expected_gap_band")
    elif previous_power is not None or next_power is not None:
        score += 0.10
        reasons.append("single_anchor_available")

    if digit >= 0.90:
        score += 0.20
        reasons.append(f"strong_digit_preservation:{digit:.3f}")
    elif digit >= 0.84:
        score += 0.16
        reasons.append(f"digit_preservation:{digit:.3f}")
    elif digit >= 0.70:
        score += 0.05
        reasons.append(f"weak_digit_preservation:{digit:.3f}")

    if candidate.get("method") == "scale_x10_truncated_digit":
        score += 0.08
        reasons.append("scale_x10_candidate")
    elif candidate.get("method") == "scale_x100_truncated_digit":
        score += 0.05
        reasons.append("scale_x100_candidate")
    elif candidate.get("method") == "insert_zero":
        score += 0.04
        reasons.append("insert_zero_candidate")

    if str(row.get("name") or "").strip():
        score += 0.06
        reasons.append("row_identity_present")
    if row.get("source_file"):
        score += 0.03
        reasons.append("source_file_present")
    if not _candidate_duplicate(value, target_rows):
        score += 0.04
        reasons.append("not_duplicate_power")
    else:
        score -= 0.20
        reasons.append("duplicate_power_candidate")

    meta = {
        "previous_anchor_power": previous_power,
        "next_anchor_power": next_power,
        "reconstructed_rank": reconstructed_rank,
        "digit_preservation_score": digit,
    }
    return round(score, 6), reasons, meta


def _promote_contextual_reconstruction(row: dict[str, Any], candidate: dict[str, Any], *, score: float, reasons: list[str], meta: dict[str, Any], ranking_type: str) -> dict[str, Any]:
    promoted = dict(row)
    power = int(candidate["value"])
    original = _power(row)
    promoted["power_original"] = original
    promoted["power_recovered_from"] = original
    promoted["power"] = power
    promoted["hero_power"] = power
    promoted["rank"] = meta.get("reconstructed_rank") or promoted.get("rank") or promoted.get("computed_rank")
    promoted["computed_rank"] = promoted["rank"]
    promoted["ranking_type"] = ranking_type
    promoted["review_ocr_attempted"] = bool(promoted.get("review_ocr_attempted", True))
    promoted["review_ocr_status"] = "contextual_reconstructed"
    promoted["review_ocr_score"] = round(score, 4)
    promoted["review_ocr_decision"] = "promoted_after_contextual_row_reconstruction"
    promoted["review_ocr_reasons"] = ";".join(reasons)
    promoted["row_reconstruction_attempted"] = True
    promoted["row_reconstruction_status"] = "promoted"
    promoted["row_reconstruction_score"] = round(score, 4)
    promoted["row_reconstruction_reason"] = ";".join(reasons)
    promoted["row_reconstruction_anchor_before_power"] = meta.get("previous_anchor_power")
    promoted["row_reconstruction_anchor_after_power"] = meta.get("next_anchor_power")
    promoted["row_reconstruction_rank"] = promoted["rank"]
    promoted["row_reconstruction_method"] = candidate.get("method")
    promoted["digit_preservation_score"] = round(float(candidate.get("digit_preservation_score") or 0.0), 4)
    promoted["power_recovery_method"] = f"{ranking_type}_contextual_row_reconstruction"
    promoted["power_recovery_status"] = "recovered"
    promoted["power_sanity_status"] = "recovered"
    promoted["power_sanity_confidence"] = round(score, 4)
    promoted["power_candidate_best"] = power
    promoted["power_candidate_best_score"] = round(score, 4)
    promoted["power_candidate_margin"] = round(score, 4)
    promoted["power_candidate_count"] = 1
    promoted["power_recovery_selected_reason"] = "contextual_row_reconstruction:" + ";".join(reasons)
    promoted["power_recovery_decision_strategy"] = "contextual_row_reconstruction"
    promoted["power_recovery_decision_version"] = "v0.9.5.54"
    promoted["power_recovery_legacy_used"] = False
    promoted["power_recovery_candidates"] = [{
        "value": power,
        "score": round(score, 4),
        "reasons": reasons,
        "digit_preservation_score": round(float(candidate.get("digit_preservation_score") or 0.0), 4),
    }]
    warning = str(promoted.get("ranking_guard_warning") or "").strip()
    suffix = "row_reconstruction:promoted_from_review"
    promoted["ranking_guard_warning"] = suffix if not warning else f"{warning};{suffix}"
    return promoted


def _attempt_contextual_row_reconstruction(row: dict[str, Any], *, target_rows: list[dict[str, Any]], ranking_type: str) -> dict[str, Any] | None:
    observed = _power(row)
    source_file = _source_file(row)
    if observed is None or not source_file or ranking_type != "total_hero_power":
        return None
    if not (1_000_000 <= observed < 50_000_000):
        return None
    source_rows = _normal_source_rows(target_rows, source_file, ranking_type)
    if len(source_rows) < 2:
        return None
    candidates = _low_truncation_candidates(observed)
    if not candidates:
        return None
    scored: list[tuple[float, dict[str, Any], list[str], dict[str, Any]]] = []
    for candidate in candidates:
        score, reasons, meta = _contextual_score(candidate, row, target_rows=target_rows, source_rows=source_rows, ranking_type=ranking_type)
        scored.append((score, candidate, reasons, meta))
    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best_candidate, best_reasons, best_meta = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0
    margin = best_score - second_score
    digit = float(best_candidate.get("digit_preservation_score") or 0.0)

    # Contextual reconstruction is intentionally conservative.  It may promote a
    # row only when anchor context and digit evidence agree.  Otherwise the row
    # stays quarantined for human review.
    if best_score < 0.82:
        return None
    if digit < 0.84:
        return None
    if margin < 0.04 and len(scored) > 1:
        return None
    if not {"bounded_by_source_anchors", "fits_anchor_power_gap"}.issubset(set(best_reasons)):
        return None
    promoted = _promote_contextual_reconstruction(row, best_candidate, score=best_score, reasons=best_reasons, meta=best_meta, ranking_type=ranking_type)
    promoted["row_reconstruction_candidate_margin"] = round(margin, 4)
    promoted["row_reconstruction_candidate_count"] = len(scored)
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

        contextual = _attempt_contextual_row_reconstruction(
            row,
            target_rows=result.get(target, []),
            ranking_type=target[1],
        )
        if contextual is not None:
            contextual["review_ocr_variants"] = len(variants)
            contextual["review_ocr_candidate_count"] = len(variant_results)
            if best:
                contextual["review_ocr_best_variant"] = best.get("review_ocr_variant")
            result.setdefault(target, []).append(contextual)
            continue

        annotated = dict(row)
        annotated["row_reconstruction_attempted"] = target[1] == "total_hero_power"
        annotated["row_reconstruction_status"] = "no_promotion" if target[1] == "total_hero_power" else "not_applicable"
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
