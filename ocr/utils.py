"""Shared OCR result helpers."""

from __future__ import annotations

from typing import Any

from ocr.provider import OCRResult


def box_bounds(box: Any) -> tuple[float, float, float, float]:
    xs = [point[0] for point in box]
    ys = [point[1] for point in box]
    return min(xs), min(ys), max(xs), max(ys)


def overlap_ratio(a: Any, b: Any) -> float:
    ax1, ay1, ax2, ay2 = box_bounds(a)
    bx1, by1, bx2, by2 = box_bounds(b)
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    area_a = max((ax2 - ax1) * (ay2 - ay1), 1.0)
    area_b = max((bx2 - bx1) * (by2 - by1), 1.0)
    return inter / min(area_a, area_b)


def deduplicate_ocr_results(
    results: list[OCRResult],
    overlap_threshold: float = 0.75,
) -> list[OCRResult]:
    """Keep highest-confidence result for heavily overlapping OCR boxes."""
    deduped: list[OCRResult] = []
    for candidate in sorted(results, key=lambda item: float(item[2]), reverse=True):
        if any(overlap_ratio(candidate[0], existing[0]) >= overlap_threshold for existing in deduped):
            continue
        deduped.append(candidate)
    return deduped
