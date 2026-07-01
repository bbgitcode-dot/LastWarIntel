"""Ranking power sanity guard.

This guard protects final ranking reconstruction from OCR digit outliers before
rows are sorted by power.  It does not repair values.  It only quarantines rows
whose power is inconsistent with the local screenshot envelope.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median
from typing import Any

QUARANTINE_KEY = ("REVIEW", "ranking_guard_quarantine")


@dataclass(frozen=True)
class RankingPowerSanityDecision:
    status: str
    confidence: float
    reasons: list[str] = field(default_factory=list)
    local_median: int | None = None
    local_ratio: float | None = None

    @property
    def should_quarantine(self) -> bool:
        return self.status == "quarantine"


def _power(row: dict[str, Any]) -> int | None:
    value = row.get("power") or row.get("hero_power") or row.get("alliance_power")
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _source_file(row: dict[str, Any]) -> str:
    return str(row.get("source_file") or "")


def _rank(row: dict[str, Any]) -> int | None:
    for key in ("ocr_rank", "rank", "computed_rank"):
        value = row.get(key)
        try:
            if value is not None and value != "":
                return int(float(value))
        except (TypeError, ValueError):
            continue
    return None


def _ocr_rank(row: dict[str, Any]) -> int | None:
    value = row.get("ocr_rank")
    try:
        if value is not None and value != "":
            return int(float(value))
    except (TypeError, ValueError):
        return None
    return None


def _safe_ratio(value: int, local_median: int | None) -> float | None:
    if not local_median or local_median <= 0:
        return None
    return value / local_median



def _source_shape_outlier_powers(rows: list[dict[str, Any]]) -> set[int]:
    """Return alliance-power values that look like source-local OCR digit explosions.

    The detector is intentionally source-local: it never relies on filename order
    or on neighbouring screenshots.  It looks only at the visible power shape of
    one screenshot/scroll block.  This protects mixed multi-user upload batches
    where screenshot ordering is arbitrary.
    """
    powers = [_power(row) for row in rows]
    powers = [value for value in powers if value is not None and value > 0]
    if len(powers) < 4:
        return set()

    outliers: set[int] = set()

    # False Alliance-Power spikes observed in the 552 mobile source are in the
    # 70B-80B range while the surrounding visible block is 20B or below.  Real
    # 550/551 leaders in the current baseline are much lower (5B-20B) and must
    # not be caught by this high-cluster detector.
    max_split = min(3, len(powers) - 2)
    for split in range(1, max_split + 1):
        high = powers[:split]
        low = powers[split:]
        low_median = int(median(low)) if low else 0
        if low_median <= 0:
            continue
        cluster_ratio = median(high) / low_median
        boundary_ratio = high[-1] / max(low[0], 1)
        if min(high) >= 50_000_000_000 and cluster_ratio >= 2.35 and boundary_ratio >= 2.25:
            outliers.update(high)

    # A high cluster at the top of a source can be an OCR digit explosion even
    # when the boundary between the first two high values is smooth.  The v0.9.5.40
    # guard caught the isolated 70B uiz row but allowed the paired 79B/77B rows
    # because their internal cluster looked consistent.  Treat the first two
    # 50B+ values as one suspicious source-local cluster when the remaining
    # visible rows sit in a much lower alliance-power envelope.
    if len(powers) >= 5 and powers[0] >= 50_000_000_000 and powers[1] >= 50_000_000_000:
        rest_median = int(median(powers[2:]))
        if rest_median > 0 and min(powers[0], powers[1]) / rest_median >= 2.35:
            outliers.update({powers[0], powers[1]})

    # A single 50B+ value at the top of a source whose remaining rows are all far
    # lower is also suspicious unless later evidence re-validates it manually.
    # This catches the isolated 70B uiz-style spike without depending on global
    # screenshot order.
    first = powers[0]
    rest_median = int(median(powers[1:])) if len(powers) > 1 else 0
    if first >= 50_000_000_000 and rest_median > 0 and first / rest_median >= 3.0:
        outliers.add(first)

    return outliers


def _mark_quarantined(
    row: dict[str, Any],
    *,
    server: object,
    ranking_type: str,
    decision: RankingPowerSanityDecision,
) -> dict[str, Any]:
    quarantined = dict(row)
    reason = ";".join(decision.reasons)
    previous_warning = str(quarantined.get("ranking_guard_warning") or "").strip()
    warning = f"power_sanity:{reason}" if reason else "power_sanity"
    quarantined["original_server"] = server if isinstance(server, int) else quarantined.get("server")
    quarantined["original_ranking_type"] = ranking_type
    quarantined["ranking_type"] = ranking_type
    quarantined["expected_ranking_type"] = ranking_type
    quarantined["ranking_guard_status"] = "quarantine"
    quarantined["ranking_guard_confidence"] = decision.confidence
    quarantined["ranking_guard_reason"] = reason
    quarantined["ranking_guard_warning"] = warning if not previous_warning else f"{previous_warning};{warning}"
    quarantined["quarantine_reason"] = "thp_power_sanity_outlier" if ranking_type == "total_hero_power" else "alliance_power_sanity_outlier"
    if decision.local_median is not None:
        quarantined["power_sanity_local_median"] = decision.local_median
    if decision.local_ratio is not None:
        quarantined["power_sanity_local_ratio"] = round(decision.local_ratio, 4)
    return quarantined


def evaluate_ranking_power_sanity(
    row: dict[str, Any],
    *,
    ranking_type: str,
    source_powers: list[int],
    is_first_source: bool,
    source_index: int = 1,
    prior_high_value_sources: int = 0,
    source_row_index: int | None = None,
    source_shape_outlier_powers: set[int] | None = None,
) -> RankingPowerSanityDecision:
    """Evaluate one row for a local power-envelope violation.

    THP keeps the v0.9.5.35 behavior: first screenshot whales are allowed, while
    late-scroll 7xx/8xx-M OCR spikes are quarantined.

    Alliance Power applies the same principle with screenshot-boundary and
    rank-aware context.  A valid top-3 alliance may be much stronger than the
    visible local tail, especially when the first ranks span two screenshots.
    Lower ranks remain tightly guarded so a single OCR digit error cannot move
    a lower-rank alliance to the top.
    """
    value = _power(row)
    if value is None or len(source_powers) < 4:
        return RankingPowerSanityDecision(status="pass", confidence=1.0, reasons=["not_applicable"])

    local_median = int(median(source_powers))
    ratio = _safe_ratio(value, local_median)
    if ratio is None:
        return RankingPowerSanityDecision(status="pass", confidence=1.0, reasons=["no_local_context"])

    if ranking_type == "total_hero_power":
        ocr_rank = _ocr_rank(row)

        # Intrinsic rank/power envelope guard. This does not depend on filename
        # order or upload order. If the row itself says it is a late-scroll rank
        # but its parsed power is in top-whale territory, the power is very likely
        # an OCR digit explosion (observed on Server 553 where ranks 100+ became
        # 764M and jumped ahead of the real top 10).
        if ocr_rank is not None:
            suspicious_late_rank = (
                (ocr_rank >= 50 and value >= 500_000_000)
                or (ocr_rank >= 80 and value >= 400_000_000)
                or (ocr_rank >= 100 and value >= 300_000_000)
            )
            if suspicious_late_rank:
                confidence = 0.99
                return RankingPowerSanityDecision(
                    status="quarantine",
                    confidence=confidence,
                    reasons=[
                        "thp_rank_power_envelope_violation",
                        f"ocr_rank:{ocr_rank}",
                        f"power:{value}",
                    ],
                    local_median=local_median,
                    local_ratio=ratio,
                )

        if is_first_source:
            return RankingPowerSanityDecision(status="pass", confidence=1.0, reasons=["first_thp_source_allowed"], local_median=local_median, local_ratio=ratio)
        if value >= 500_000_000 and ratio >= 2.0:
            confidence = min(0.99, round((ratio - 1.0) / 3.0 + 0.66, 4))
            return RankingPowerSanityDecision(
                status="quarantine",
                confidence=confidence,
                reasons=[
                    "thp_power_outlier",
                    "late_scroll_source",
                    f"power_to_local_median_ratio:{ratio:.2f}",
                ],
                local_median=local_median,
                local_ratio=ratio,
            )
        return RankingPowerSanityDecision(status="pass", confidence=1.0, reasons=["thp_power_sanity_validated"], local_median=local_median, local_ratio=ratio)

    if ranking_type == "alliance_power":
        rank = _rank(row)
        source_shape_outlier_powers = source_shape_outlier_powers or set()

        # Absolute safety cap is evaluated before source-shape detection so an
        # impossible value is explained as such, not merely as a local cluster.
        if value >= 150_000_000_000:
            confidence = 0.99
            return RankingPowerSanityDecision(
                status="quarantine",
                confidence=confidence,
                reasons=[
                    "alliance_power_outlier",
                    "absolute_power_ceiling",
                    f"power_to_local_median_ratio:{ratio:.2f}",
                ],
                local_median=local_median,
                local_ratio=ratio,
            )

        ocr_rank = _ocr_rank(row)
        if ocr_rank is not None and ocr_rank >= 4 and value >= 50_000_000_000:
            confidence = 0.99
            return RankingPowerSanityDecision(
                status="quarantine",
                confidence=confidence,
                reasons=[
                    "alliance_rank_power_envelope_violation",
                    f"ocr_rank:{ocr_rank}",
                    f"power:{value}",
                    f"power_to_local_median_ratio:{ratio:.2f}",
                ],
                local_median=local_median,
                local_ratio=ratio,
            )

        if value in source_shape_outlier_powers:
            confidence = min(0.99, round((ratio - 1.0) / 2.5 + 0.70, 4))
            return RankingPowerSanityDecision(
                status="quarantine",
                confidence=confidence,
                reasons=[
                    "alliance_power_outlier",
                    "source_shape_high_cluster",
                    f"power_to_local_median_ratio:{ratio:.2f}",
                ],
                local_median=local_median,
                local_ratio=ratio,
            )

        # Top alliance rows are allowed to be much stronger than a screenshot's
        # local median.  In mobile captures OCR rank anchors can be missing before
        # final reconstruction, so rank-only grace is not enough: the first two
        # alliance-power screenshots may contain the real top-3 leaders even when
        # rows only have computed ranks later during export.  Keep this allowance
        # narrow: it applies only to very high alliance-scale values in the first
        # two source screenshots and still respects the absolute ceiling above.
        if rank is not None and rank <= 3:
            return RankingPowerSanityDecision(
                status="pass",
                confidence=1.0,
                reasons=["alliance_power_top_rank_boundary_allowed"],
                local_median=local_median,
                local_ratio=ratio,
            )

        if (
            rank is None
            and source_index <= 2
            and value >= 50_000_000_000
            and (source_index == 1 or prior_high_value_sources >= 1)
        ):
            return RankingPowerSanityDecision(
                status="pass",
                confidence=1.0,
                reasons=["alliance_power_early_source_high_value_allowed"],
                local_median=local_median,
                local_ratio=ratio,
            )

        # General top-of-screenshot allowance: desktop and mobile captures can
        # split a server's real top alliances across multiple screenshots.  When
        # OCR rank anchors are unavailable before final reconstruction, the first
        # rows of a screenshot may look like median outliers even though they are
        # simply the visible top of that scroll block.  Allow only the first two
        # visual rows of a source screenshot and keep the absolute ceiling above;
        # later rows in the same source still use the strict local envelope.
        if (
            rank is None
            and source_row_index is not None
            and source_row_index <= 2
            and value >= 1_000_000_000
        ):
            return RankingPowerSanityDecision(
                status="pass",
                confidence=1.0,
                reasons=["alliance_power_source_top_row_allowed"],
                local_median=local_median,
                local_ratio=ratio,
            )

        threshold = 2.35
        is_source_top_grace_row = source_row_index is not None and source_row_index <= 2
        if value >= 5_000_000_000 and ratio >= threshold and not is_source_top_grace_row:
            confidence = min(0.99, round((ratio - 1.0) / 2.5 + 0.62, 4))
            return RankingPowerSanityDecision(
                status="quarantine",
                confidence=confidence,
                reasons=[
                    "alliance_power_outlier",
                    f"power_to_local_median_ratio:{ratio:.2f}",
                ],
                local_median=local_median,
                local_ratio=ratio,
            )
        return RankingPowerSanityDecision(status="pass", confidence=1.0, reasons=["alliance_power_sanity_validated"], local_median=local_median, local_ratio=ratio)

    return RankingPowerSanityDecision(status="pass", confidence=1.0, reasons=["ranking_type_not_guarded"], local_median=local_median, local_ratio=ratio)


def apply_ranking_power_sanity_guard(
    grouped: dict[tuple[object, str], list[dict[str, Any]]]
) -> dict[tuple[object, str], list[dict[str, Any]]]:
    """Quarantine ranking power outliers without modifying trusted values."""
    guarded: dict[tuple[object, str], list[dict[str, Any]]] = {}
    quarantined_rows: list[dict[str, Any]] = []

    for key, rows in grouped.items():
        server, ranking_type = key
        if ranking_type not in {"total_hero_power", "alliance_power"} or not isinstance(server, int):
            guarded.setdefault(key, []).extend(rows)
            continue

        by_source: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            by_source.setdefault(_source_file(row), []).append(row)

        sorted_sources = sorted(by_source)
        prior_high_value_sources = 0
        for source_index, source in enumerate(sorted_sources, start=1):
            source_rows = by_source[source]
            source_powers = [_power(row) for row in source_rows]
            source_powers = [value for value in source_powers if value is not None]
            is_first_source = source_index == 1
            current_source_high_values = sum(1 for value in source_powers if value >= 50_000_000_000)
            source_shape_outlier_powers = _source_shape_outlier_powers(source_rows) if ranking_type == "alliance_power" else set()
            for source_row_index, row in enumerate(source_rows, start=1):
                decision = evaluate_ranking_power_sanity(
                    row,
                    ranking_type=ranking_type,
                    source_powers=source_powers,
                    is_first_source=is_first_source,
                    source_index=source_index,
                    prior_high_value_sources=prior_high_value_sources,
                    source_row_index=source_row_index,
                    source_shape_outlier_powers=source_shape_outlier_powers,
                )
                if decision.should_quarantine:
                    quarantined_rows.append(
                        _mark_quarantined(row, server=server, ranking_type=ranking_type, decision=decision)
                    )
                else:
                    row.setdefault("power_sanity_status", "validated")
                    row.setdefault("power_sanity_confidence", decision.confidence)
                    if ranking_type == "total_hero_power":
                        row.setdefault("thp_sanity_status", "validated")
                        row.setdefault("thp_sanity_confidence", decision.confidence)
                    guarded.setdefault(key, []).append(row)
            if current_source_high_values >= 2:
                prior_high_value_sources += 1

    if quarantined_rows:
        guarded.setdefault(QUARANTINE_KEY, []).extend(quarantined_rows)

    return guarded


# Backward-compatible alias for v0.9.5.35 tests and integrations.
def apply_thp_power_sanity_guard(
    grouped: dict[tuple[object, str], list[dict[str, Any]]]
) -> dict[tuple[object, str], list[dict[str, Any]]]:
    return apply_ranking_power_sanity_guard(grouped)
