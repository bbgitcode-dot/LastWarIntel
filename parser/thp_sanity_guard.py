"""THP power sanity guard.

This guard protects Total Hero Power rankings from OCR digit outliers after row
parsing but before final power-order merge. It does not repair values. It only
quarantines rows whose power is inconsistent with the surrounding screenshot and
with the already-seen scroll sequence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median
from typing import Any

QUARANTINE_KEY = ("REVIEW", "ranking_guard_quarantine")


@dataclass(frozen=True)
class ThpPowerSanityDecision:
    status: str
    confidence: float
    reasons: list[str] = field(default_factory=list)
    local_median: int | None = None

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


def _mark_quarantined(row: dict[str, Any], *, server: object, decision: ThpPowerSanityDecision) -> dict[str, Any]:
    quarantined = dict(row)
    reason = ";".join(decision.reasons)
    previous_warning = str(quarantined.get("ranking_guard_warning") or "").strip()
    warning = f"thp_power_sanity:{reason}" if reason else "thp_power_sanity"
    quarantined["original_server"] = server if isinstance(server, int) else quarantined.get("server")
    quarantined["original_ranking_type"] = "total_hero_power"
    quarantined["ranking_type"] = "total_hero_power"
    quarantined["expected_ranking_type"] = "total_hero_power"
    quarantined["ranking_guard_status"] = "quarantine"
    quarantined["ranking_guard_confidence"] = decision.confidence
    quarantined["ranking_guard_reason"] = reason
    quarantined["ranking_guard_warning"] = warning if not previous_warning else f"{previous_warning};{warning}"
    quarantined["quarantine_reason"] = "thp_power_sanity_outlier"
    if decision.local_median is not None:
        quarantined["thp_sanity_local_median"] = decision.local_median
    return quarantined


def evaluate_thp_power_sanity(
    row: dict[str, Any],
    *,
    source_powers: list[int],
    is_first_source: bool,
) -> ThpPowerSanityDecision:
    """Evaluate one THP row for impossible late-scroll power spikes.

    The first THP screenshot is allowed to contain genuine whales. On later
    screenshots, a power value that is more than twice the local screenshot
    median is treated as an OCR digit outlier candidate. This catches cases like
    198M being read as 798M while allowing normal overlap between adjacent scroll
    screenshots.
    """
    value = _power(row)
    if value is None or is_first_source or len(source_powers) < 4:
        return ThpPowerSanityDecision(status="pass", confidence=1.0, reasons=["not_applicable"])

    # Median of the screenshot gives strong local context and ignores one or two
    # OCR spikes at the top of the same screenshot.
    local_median = int(median(source_powers))
    if local_median <= 0:
        return ThpPowerSanityDecision(status="pass", confidence=1.0, reasons=["no_local_context"])

    ratio = value / local_median
    if value >= 500_000_000 and ratio >= 2.0:
        confidence = min(0.99, round((ratio - 1.0) / 3.0 + 0.66, 4))
        return ThpPowerSanityDecision(
            status="quarantine",
            confidence=confidence,
            reasons=[
                "thp_power_outlier",
                "late_scroll_source",
                f"power_to_local_median_ratio:{ratio:.2f}",
            ],
            local_median=local_median,
        )

    return ThpPowerSanityDecision(status="pass", confidence=1.0, reasons=["thp_power_sanity_validated"], local_median=local_median)


def apply_thp_power_sanity_guard(
    grouped: dict[tuple[object, str], list[dict[str, Any]]]
) -> dict[tuple[object, str], list[dict[str, Any]]]:
    """Quarantine THP power outliers without modifying trusted values."""
    guarded: dict[tuple[object, str], list[dict[str, Any]]] = {}
    quarantined_rows: list[dict[str, Any]] = []

    for key, rows in grouped.items():
        server, ranking_type = key
        if ranking_type != "total_hero_power" or not isinstance(server, int):
            guarded.setdefault(key, []).extend(rows)
            continue

        by_source: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            by_source.setdefault(_source_file(row), []).append(row)

        for source_index, source in enumerate(sorted(by_source), start=1):
            source_rows = by_source[source]
            source_powers = [_power(row) for row in source_rows]
            source_powers = [value for value in source_powers if value is not None]
            is_first_source = source_index == 1
            for row in source_rows:
                decision = evaluate_thp_power_sanity(
                    row,
                    source_powers=source_powers,
                    is_first_source=is_first_source,
                )
                if decision.should_quarantine:
                    quarantined_rows.append(_mark_quarantined(row, server=server, decision=decision))
                else:
                    row.setdefault("thp_sanity_status", "validated")
                    row.setdefault("thp_sanity_confidence", decision.confidence)
                    guarded.setdefault(key, []).append(row)

    if quarantined_rows:
        guarded.setdefault(QUARANTINE_KEY, []).extend(quarantined_rows)

    return guarded
