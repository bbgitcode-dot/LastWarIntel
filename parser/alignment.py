"""Bounding-box based row alignment for ranking screenshots.

The old parser reconstructed ranking rows mostly from OCR text order and broad
Y clustering. That is fragile for Last War ranking cards: OCR frequently emits
rank, commander name, alliance tag and power as independent boxes and sometimes
slightly shifts the Y position of one field. This module treats OCR output as
layout evidence first and text second.

The core idea:

1. Convert OCR results into tokens with geometry.
2. Use power values as strong row anchors.
3. Pair optional rank tokens by nearest Y position.
4. Build row bands from neighbouring anchors.
5. Collect only tokens inside the band and left of the row's power value.

This prevents the common failure mode where the name from one card is assigned
to the power or rank of the next card.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class OcrToken:
    """OCR text with normalized bounding-box geometry."""

    text: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float
    cx: float
    cy: float

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1


@dataclass
class AlignedRankingRow:
    """A reconstructed ranking row before domain parsing."""

    y: float
    y_top: float
    y_bottom: float
    tokens: list[OcrToken] = field(default_factory=list)
    rank_token: OcrToken | None = None
    power_token: OcrToken | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def texts(self) -> list[str]:
        return [token.text for token in sorted(self.tokens, key=lambda item: item.cx)]

    @property
    def confidence(self) -> float:
        if not self.tokens:
            return 0.0
        return min(token.confidence for token in self.tokens)


def token_from_ocr_result(result) -> OcrToken:
    """Convert an EasyOCR-compatible result tuple into an OcrToken."""
    box, text, confidence = result
    xs = [point[0] for point in box]
    ys = [point[1] for point in box]
    x1, x2 = min(xs), max(xs)
    y1, y2 = min(ys), max(ys)
    return OcrToken(
        text=str(text or ""),
        confidence=float(confidence or 0.0),
        x1=float(x1),
        y1=float(y1),
        x2=float(x2),
        y2=float(y2),
        cx=float(sum(xs) / len(xs)),
        cy=float(sum(ys) / len(ys)),
    )


def tokens_from_ocr_results(ocr_results: Iterable) -> list[OcrToken]:
    return [token_from_ocr_result(result) for result in ocr_results]


def _cluster_tokens_by_y(tokens: list[OcrToken], tolerance: float) -> list[list[OcrToken]]:
    """Cluster tokens by vertical center."""
    clusters: list[list[OcrToken]] = []
    for token in sorted(tokens, key=lambda item: item.cy):
        best_cluster = None
        best_distance = None
        for cluster in clusters:
            cluster_y = sum(item.cy for item in cluster) / len(cluster)
            distance = abs(cluster_y - token.cy)
            if distance <= tolerance and (best_distance is None or distance < best_distance):
                best_cluster = cluster
                best_distance = distance
        if best_cluster is None:
            clusters.append([token])
        else:
            best_cluster.append(token)
    return clusters


def _choose_representative_power(cluster: list[OcrToken], clean_power) -> OcrToken:
    """Choose the best power token from a vertical cluster.

    Prefer the right-most token because power values are rendered in the right
    column. If there are duplicates from multiple OCR readers, this keeps the
    geometrically strongest row anchor.
    """
    return max(cluster, key=lambda token: (token.cx, token.confidence, len(token.text)))


def _derive_row_height(anchors: list[float]) -> float:
    if len(anchors) < 2:
        return 58.0
    gaps = [b - a for a, b in zip(anchors, anchors[1:]) if b > a]
    if not gaps:
        return 58.0
    gaps.sort()
    median_gap = gaps[len(gaps) // 2]
    return max(36.0, min(90.0, median_gap))


def build_aligned_ranking_rows(
    ocr_results,
    *,
    is_power,
    clean_power,
    is_rank,
    is_noise,
    is_warzone,
    min_y: float = 90.0,
    power_y_tolerance: float = 20.0,
    rank_y_tolerance: float = 34.0,
) -> list[AlignedRankingRow]:
    """Build layout-aligned ranking rows from OCR results.

    Parameters are dependency-injected so this module stays purely geometric and
    can be tested without importing domain-specific parser functions.
    """
    tokens = []
    for token in tokens_from_ocr_results(ocr_results):
        if token.cy < min_y:
            continue
        if not token.text.strip():
            continue
        if is_noise(token.text) or is_warzone(token.text):
            continue
        tokens.append(token)

    power_tokens = [token for token in tokens if is_power(token.text)]
    if not power_tokens:
        return []

    rank_tokens = [token for token in tokens if is_rank(token.text)]

    # Cluster power tokens first. Each visible Last War row has one relevant
    # power value. Multiple OCR providers may produce duplicates around the same
    # Y position; these must not create duplicate rows.
    power_clusters = _cluster_tokens_by_y(power_tokens, tolerance=power_y_tolerance)
    power_anchors = [_choose_representative_power(cluster, clean_power) for cluster in power_clusters]
    power_anchors.sort(key=lambda token: token.cy)

    row_centers = [token.cy for token in power_anchors]
    row_height = _derive_row_height(row_centers)

    rows: list[AlignedRankingRow] = []
    for index, power_token in enumerate(power_anchors):
        if index == 0:
            y_top = power_token.cy - row_height / 2
        else:
            y_top = (power_anchors[index - 1].cy + power_token.cy) / 2

        if index == len(power_anchors) - 1:
            y_bottom = power_token.cy + row_height / 2
        else:
            y_bottom = (power_token.cy + power_anchors[index + 1].cy) / 2

        row = AlignedRankingRow(
            y=power_token.cy,
            y_top=y_top,
            y_bottom=y_bottom,
            power_token=power_token,
        )

        # Find the nearest rank token left of the power column. A hard row band
        # alone is not enough because rank OCR is often vertically offset by a
        # few pixels compared with the name/power text baseline.
        candidate_ranks = [
            token for token in rank_tokens
            if token.cx < power_token.cx and abs(token.cy - power_token.cy) <= rank_y_tolerance
        ]
        if candidate_ranks:
            row.rank_token = min(candidate_ranks, key=lambda token: abs(token.cy - power_token.cy))
        else:
            row.warnings.append("missing_rank_anchor")

        # Collect tokens that belong to this row's vertical band. Power and rank
        # tokens are kept; downstream parsing decides what to use for fields.
        band_tokens = [
            token for token in tokens
            if y_top <= token.cy < y_bottom
            and token.cx <= power_token.x2 + 20
        ]

        # If the nearest rank token lies just outside the band, keep it anyway.
        if row.rank_token and row.rank_token not in band_tokens:
            band_tokens.append(row.rank_token)
            row.warnings.append("rank_anchor_outside_row_band")

        if power_token not in band_tokens:
            band_tokens.append(power_token)

        row.tokens = sorted(band_tokens, key=lambda token: token.cx)
        rows.append(row)

    return rows
