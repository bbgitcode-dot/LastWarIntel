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
) -> RankingPowerSanityDecision:
    """Evaluate one row for a local power-envelope violation.

    THP keeps the v0.9.5.35 behavior: first screenshot whales are allowed, while
    late-scroll 7xx/8xx-M OCR spikes are quarantined.

    Alliance Power applies the same principle to every screenshot, but with a
    stricter local envelope because alliance lists are usually monotonic and a
    single OCR digit error can otherwise move a lower-rank alliance to the top.
    The first visible ranks get a small grace window so a real leading alliance
    is not quarantined merely for being stronger than the pack.
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
        # A real rank-1 or rank-2 alliance can be materially stronger.  Lower
        # ranks should not suddenly be 2.4x+ above their local screenshot peers.
        rank_grace = rank is not None and rank <= 2
        threshold = 3.5 if rank_grace else 2.35
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

        for source_index, source in enumerate(sorted(by_source), start=1):
            source_rows = by_source[source]
            source_powers = [_power(row) for row in source_rows]
            source_powers = [value for value in source_powers if value is not None]
            is_first_source = source_index == 1
            for row in source_rows:
                decision = evaluate_ranking_power_sanity(
                    row,
                    ranking_type=ranking_type,
                    source_powers=source_powers,
                    is_first_source=is_first_source,
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

    if quarantined_rows:
        guarded.setdefault(QUARANTINE_KEY, []).extend(quarantined_rows)

    return guarded


# Backward-compatible alias for v0.9.5.35 tests and integrations.
def apply_thp_power_sanity_guard(
    grouped: dict[tuple[object, str], list[dict[str, Any]]]
) -> dict[tuple[object, str], list[dict[str, Any]]]:
    return apply_ranking_power_sanity_guard(grouped)
