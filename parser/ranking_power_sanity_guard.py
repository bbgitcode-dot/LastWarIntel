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


def _safe_ratio(value: int, local_median: int | None) -> float | None:
    if not local_median or local_median <= 0:
        return None
    return value / local_median


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

        # Absolute safety cap: Last War alliance-power screenshots in the current
        # baseline are nowhere near this range.  Keep a hard ceiling so rank-aware
        # grace cannot accidentally bless a catastrophic digit explosion.
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

        threshold = 2.35
        if value >= 5_000_000_000 and ratio >= threshold:
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
            for row in source_rows:
                decision = evaluate_ranking_power_sanity(
                    row,
                    ranking_type=ranking_type,
                    source_powers=source_powers,
                    is_first_source=is_first_source,
                    source_index=source_index,
                    prior_high_value_sources=prior_high_value_sources,
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
