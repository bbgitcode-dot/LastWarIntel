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
class PowerRecoveryCandidate:
    value: int
    score: float
    reasons: list[str] = field(default_factory=list)


def _candidate_dict(candidate: PowerRecoveryCandidate) -> dict[str, Any]:
    return {
        "value": candidate.value,
        "score": round(candidate.score, 4),
        "reasons": list(candidate.reasons),
    }


def _source_low_powers_for_recovery(*, ranking_type: str, source_powers: list[int], observed: int) -> list[int]:
    if ranking_type == "total_hero_power":
        return [power for power in source_powers if 50_000_000 <= power < min(observed, 350_000_000)]
    if ranking_type == "alliance_power":
        return [power for power in source_powers if 500_000_000 <= power < min(observed, 45_000_000_000)]
    return []


def _generate_power_recovery_candidates(
    row: dict[str, Any],
    *,
    ranking_type: str,
    source_powers: list[int],
) -> list[int]:
    """Generate plausible corrected power values for a suspicious OCR value.

    Candidate generation is deliberately context-aware but source-local.  It does
    not use filename order, upload order, or neighbouring screenshots as truth.
    It combines the old leading-digit correction with candidates derived from the
    visible local power envelope.  This lets Server 553-style values such as
    764M consider 164M and 224M instead of blindly choosing 164M.
    """
    observed = _power(row)
    if observed is None:
        return []
    text = str(observed)
    if len(text) < 8 or text[0] not in {"7", "8"}:
        return []

    values: set[int] = set()

    if ranking_type == "total_hero_power" and 500_000_000 <= observed < 1_000_000_000:
        for leading in (1, 2, 3):
            candidate = int(str(leading) + text[1:])
            if 80_000_000 <= candidate <= 350_000_000:
                values.add(candidate)

        tail = observed % 1_000_000
        for low in _source_low_powers_for_recovery(ranking_type=ranking_type, source_powers=source_powers, observed=observed):
            million_prefix = low // 1_000_000
            candidate = million_prefix * 1_000_000 + tail
            if 80_000_000 <= candidate <= 350_000_000:
                values.add(candidate)

    elif ranking_type == "alliance_power" and 50_000_000_000 <= observed < 150_000_000_000:
        for leading in (1, 2, 3, 4):
            candidate = int(str(leading) + text[1:])
            if 1_000_000_000 <= candidate <= 45_000_000_000:
                values.add(candidate)

        tail = observed % 1_000_000_000
        for low in _source_low_powers_for_recovery(ranking_type=ranking_type, source_powers=source_powers, observed=observed):
            billion_prefix = low // 1_000_000_000
            candidate = billion_prefix * 1_000_000_000 + tail
            if 1_000_000_000 <= candidate <= 45_000_000_000:
                values.add(candidate)

    return sorted(values)


def _score_power_recovery_candidates(
    row: dict[str, Any],
    *,
    ranking_type: str,
    source_rows: list[dict[str, Any]],
    source_powers: list[int],
    source_row_index: int | None,
) -> list[PowerRecoveryCandidate]:
    observed = _power(row)
    if observed is None:
        return []
    raw_candidates = _generate_power_recovery_candidates(row, ranking_type=ranking_type, source_powers=source_powers)
    if not raw_candidates:
        return []

    index = source_row_index - 1 if source_row_index is not None else None
    prior_lows: list[int] = []
    following_lows: list[int] = []
    row_rank = _ocr_rank(row)
    ranked_context_available = row_rank is not None and any(_ocr_rank(context_row) is not None for context_row in source_rows)
    if ranked_context_available:
        for context_row in source_rows:
            if context_row is row:
                continue
            context_rank = _ocr_rank(context_row)
            power = _power(context_row)
            if context_rank is None or power is None:
                continue
            recovered_context = _source_low_powers_for_recovery(ranking_type=ranking_type, source_powers=[power], observed=observed)
            if context_rank < row_rank:
                prior_lows.extend(recovered_context)
            elif context_rank > row_rank:
                following_lows.extend(recovered_context)
    elif index is not None:
        for prior in source_rows[:index]:
            power = _power(prior)
            if power is not None:
                prior_lows.extend(_source_low_powers_for_recovery(ranking_type=ranking_type, source_powers=[power], observed=observed))
        for following in source_rows[index + 1:]:
            power = _power(following)
            if power is not None:
                following_lows.extend(_source_low_powers_for_recovery(ranking_type=ranking_type, source_powers=[power], observed=observed))

    low_values = _source_low_powers_for_recovery(ranking_type=ranking_type, source_powers=source_powers, observed=observed)
    low_median = int(median(low_values)) if low_values else None
    scale = 1_000_000 if ranking_type == "total_hero_power" else 1_000_000_000
    candidates: list[PowerRecoveryCandidate] = []

    for value in raw_candidates:
        score = 0.0
        reasons: list[str] = []

        if low_median:
            distance = abs(value - low_median) / max(low_median, 1)
            local_score = max(0.0, 1.0 - distance) * 0.28
            score += local_score
            reasons.append(f"local_median_distance:{distance:.3f}")

        if prior_lows:
            nearest_prior = min(prior_lows, key=lambda power: abs(power - value))
            if nearest_prior >= value:
                score += 0.24
                reasons.append("fits_prior_neighbour_order")
            elif abs(nearest_prior - value) <= 1.5 * scale:
                score += 0.12
                reasons.append("near_prior_neighbour")
            else:
                score -= 0.18
                reasons.append("breaks_prior_neighbour_order")

        if following_lows:
            nearest_following = min(following_lows, key=lambda power: abs(power - value))
            if value >= nearest_following:
                score += 0.24
                reasons.append("fits_following_neighbour_order")
            elif abs(nearest_following - value) <= 1.5 * scale:
                score += 0.12
                reasons.append("near_following_neighbour")
            else:
                score -= 0.18
                reasons.append("breaks_following_neighbour_order")

        # Prefer candidates that do not invent a new power tier when a same-tier
        # source-local row already exists. This keeps the old 164M/17B cases
        # stable, but allows 224M/27B when the local envelope points there.
        same_bucket_hits = [power for power in low_values if abs((power // scale) - (value // scale)) <= 1]
        if same_bucket_hits:
            score += 0.18
            reasons.append("source_local_bucket_match")

        ocr_rank = _ocr_rank(row)
        if ranking_type == "total_hero_power" and ocr_rank is not None and ocr_rank >= 50:
            score += 0.10
            reasons.append(f"late_thp_rank:{ocr_rank}")
        if ranking_type == "alliance_power" and ((ocr_rank is not None and ocr_rank >= 4) or (source_row_index is not None and source_row_index >= 3)):
            score += 0.10
            reasons.append("non_top_alliance_context")

        # Small penalty for candidates that remain too close to the observed OCR
        # explosion, because they likely preserve the false leading magnitude.
        if value >= observed * 0.50:
            score -= 0.12
            reasons.append("too_close_to_observed_explosion")

        candidates.append(PowerRecoveryCandidate(value=value, score=round(score, 6), reasons=reasons))

    candidates.sort(key=lambda candidate: (candidate.score, -abs(candidate.value - (low_median or candidate.value))), reverse=True)
    return candidates


def _recover_context_power(
    row: dict[str, Any],
    *,
    ranking_type: str,
    source_rows: list[dict[str, Any]],
    source_powers: list[int],
    source_row_index: int | None,
) -> tuple[int | None, list[PowerRecoveryCandidate], str]:
    candidates = _score_power_recovery_candidates(
        row,
        ranking_type=ranking_type,
        source_rows=source_rows,
        source_powers=source_powers,
        source_row_index=source_row_index,
    )
    if not candidates:
        return None, [], "no_candidates"

    best = candidates[0]
    second_score = candidates[1].score if len(candidates) > 1 else 0.0
    margin = best.score - second_score

    if best.score >= 0.58 and margin >= 0.10:
        return best.value, candidates, f"selected_clear_candidate:score={best.score:.3f};margin={margin:.3f}"
    return None, candidates, f"ambiguous_candidates:best={best.score:.3f};margin={margin:.3f}"


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




def _set_power(row: dict[str, Any], value: int) -> None:
    """Update the canonical and typed power fields in-place."""
    row["power"] = value
    if row.get("hero_power") is not None:
        row["hero_power"] = value
    if row.get("alliance_power") is not None:
        row["alliance_power"] = value


def _recover_leading_digit_power(
    row: dict[str, Any],
    *,
    ranking_type: str,
    source_powers: list[int],
    source_row_index: int | None,
) -> int | None:
    """Recover source-local leading-digit explosions when rank/context agree.

    This is intentionally narrow.  It handles the observed mobile OCR class where
    a late THP value like ``164,292,586`` becomes ``764,292,586`` and an Alliance
    Power value like ``17,739,565,950`` becomes ``77,739,565,950``.  The function
    does not use filename or upload order; it requires intrinsic row/source
    context before returning a replacement value.
    """
    value = _power(row)
    if value is None:
        return None
    text = str(value)
    if len(text) < 8 or text[0] not in {"7", "8"}:
        return None

    ocr_rank = _ocr_rank(row)
    low_values = [power for power in source_powers if 0 < power < value and power < 300_000_000]
    low_median = int(median(low_values)) if low_values else None

    if ranking_type == "total_hero_power":
        if value < 500_000_000 or value >= 1_000_000_000:
            return None
        candidate = int("1" + text[1:])
        if not (100_000_000 <= candidate <= 300_000_000):
            return None

        # Strongest evidence: the row itself carries a late-scroll OCR rank.
        # Real 700M+ top rows have low OCR ranks and must not be rewritten.
        if ocr_rank is not None and ocr_rank >= 50:
            return candidate

        # Secondary evidence: source-local low envelope exists and the candidate
        # falls back into that envelope while the observed value is a 3x+ spike.
        if low_median and value / low_median >= 3.0 and 0.70 <= candidate / low_median <= 1.35:
            return candidate
        return None

    if ranking_type == "alliance_power":
        if value < 50_000_000_000 or value >= 100_000_000_000:
            return None
        candidate = int("1" + text[1:])
        if not (1_000_000_000 <= candidate <= 40_000_000_000):
            return None

        # Rank/context evidence: the row is not a top-3 leader but the value is
        # 50B+.  Recover to the plausible 10B/17B/19B class instead of dropping
        # the alliance entirely.
        if ocr_rank is not None and ocr_rank >= 4:
            return candidate
        if source_row_index is not None and source_row_index >= 3:
            return candidate

        # Source-local low envelope catch for missing rank anchors.
        local_lows = [power for power in source_powers if 0 < power < 40_000_000_000]
        if len(local_lows) >= 3:
            local_median = int(median(local_lows))
            if local_median > 0 and value / local_median >= 2.35 and 0.55 <= candidate / local_median <= 1.85:
                return candidate
        return None

    return None


def _apply_recovered_power(
    row: dict[str, Any],
    recovered_power: int,
    *,
    method: str,
    candidates: list[PowerRecoveryCandidate] | None = None,
    decision_reason: str | None = None,
) -> dict[str, Any]:
    recovered = dict(row)
    original = _power(recovered)
    if original is None or original == recovered_power:
        return recovered
    recovered["power_original"] = original
    recovered["power_recovered_from"] = original
    recovered["power_recovery_method"] = method
    recovered["power_sanity_status"] = "recovered"
    if candidates:
        recovered["power_recovery_candidates"] = [_candidate_dict(candidate) for candidate in candidates]
        selected = next((candidate for candidate in candidates if candidate.value == recovered_power), candidates[0])
        recovered["power_recovery_selected_score"] = round(selected.score, 4)
        recovered["power_recovery_selected_reason"] = decision_reason or ";".join(selected.reasons)
        recovered["power_sanity_confidence"] = min(0.99, max(0.50, round(selected.score, 4)))
    else:
        recovered["power_sanity_confidence"] = 0.95
    previous_warning = str(recovered.get("ranking_guard_warning") or "").strip()
    warning = f"power_sanity:context_candidate_recovered:{original}->{recovered_power}"
    recovered["ranking_guard_warning"] = warning if not previous_warning else f"{previous_warning};{warning}"
    _set_power(recovered, recovered_power)
    return recovered


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



def _row_has_rank_conflict(row: dict[str, Any]) -> bool:
    warning = str(row.get("rank_warning") or "")
    if "ocr_rank_differs_from_power_rank" in warning:
        return True
    ocr = _ocr_rank(row)
    computed = row.get("computed_rank")
    try:
        computed_int = int(float(computed)) if computed is not None and computed != "" else None
    except (TypeError, ValueError):
        computed_int = None
    return ocr is not None and computed_int is not None and ocr != computed_int


def _thp_source_digit_explosion_powers(rows: list[dict[str, Any]]) -> set[int]:
    """Return THP values that look like source-local OCR leading-digit explosions.

    Some mobile screenshots produce a mixed source where late-scroll rows around
    160M are correctly present, while a few neighbouring rows from the same
    visual block are read as 760M/790M and jump to the top after global sorting.
    The detector is strictly source-local: it does not use filename order, upload
    order, or neighbouring screenshots.  v0.9.5.44 also catches a compact high
    cluster even when one row lacks a rank-conflict warning, because the whole
    cluster shares the same impossible 7xx/8xx-M envelope while the visible
    source median remains in normal 160M-250M territory.
    """
    values: list[int] = []
    for row in rows:
        value = _power(row)
        if value is not None and value > 0:
            values.append(value)
    if len(values) < 6:
        return set()

    low_values = [value for value in values if value < 300_000_000]
    high_values = [value for value in values if value >= 500_000_000]
    if len(low_values) < 3 or not high_values:
        return set()

    low_median = int(median(low_values))
    if low_median <= 0 or min(high_values) / low_median < 3.0:
        return set()

    outliers: set[int] = set()
    rank_conflict_high_values: set[int] = set()
    for row in rows:
        value = _power(row)
        if value is None or value < 500_000_000:
            continue
        if _row_has_rank_conflict(row):
            rank_conflict_high_values.add(value)

    outliers.update(rank_conflict_high_values)

    # Cluster catch: if a source contains multiple 500M+ rows, most of them
    # already have rank-conflict evidence, and the low envelope is normal THP,
    # the remaining neighbouring high row is the same OCR digit-explosion class.
    # This closes the Server 553 case where Crank40 survived while adjacent
    # 764M/763M rows were correctly quarantined.
    if len(high_values) >= 2 and len(rank_conflict_high_values) >= max(1, len(high_values) - 1):
        outliers.update(high_values)

    # Pure source-shape catch: a compact high cluster at the top of one visual
    # source followed by a stable low envelope is also unsafe, even when rank
    # warnings are incomplete.  Keep the threshold high to avoid real whale rows.
    max_split = min(4, len(values) - 3)
    for split in range(2, max_split + 1):
        high = values[:split]
        low = values[split:]
        if min(high) < 500_000_000:
            continue
        low_median_for_split = int(median([value for value in low if value < 300_000_000])) if low else 0
        if low_median_for_split > 0 and min(high) / low_median_for_split >= 3.0:
            outliers.update(high)

    return outliers


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

    # Source-local middle spike: if a 50B+ value appears after multiple lower
    # visible rows from the same screenshot, it is not a legitimate top-of-source
    # leader.  Server 553 exposed this as [kk7] Barb being read as 77.7B at
    # visual rank 5 although the surrounding rank-1..4 alliance powers are
    # 27.8B/25.8B/18.4B/17.2B.  This rule remains local and does not assume any
    # order between screenshots or uploaders.
    for index, value in enumerate(powers):
        if index < 2 or value < 50_000_000_000:
            continue
        prior = [prior_value for prior_value in powers[:index] if prior_value < 40_000_000_000]
        following = [next_value for next_value in powers[index + 1:] if next_value < 40_000_000_000]
        if len(prior) >= 2 and following:
            local_low = int(median(prior + following))
            if local_low > 0 and value / local_low >= 2.35:
                outliers.add(value)

    return outliers


def _mark_quarantined(
    row: dict[str, Any],
    *,
    server: object,
    ranking_type: str,
    decision: RankingPowerSanityDecision,
    recovery_candidates: list[PowerRecoveryCandidate] | None = None,
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
    if recovery_candidates:
        quarantined["power_recovery_candidates"] = [_candidate_dict(candidate) for candidate in recovery_candidates]
        quarantined["power_recovery_selected_reason"] = "quarantined_ambiguous_candidates"
        quarantined["power_sanity_status"] = "candidate_ambiguous"
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
    thp_source_digit_explosion_powers: set[int] | None = None,
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
        thp_source_digit_explosion_powers = thp_source_digit_explosion_powers or set()

        if value in thp_source_digit_explosion_powers:
            confidence = min(0.99, round((ratio - 1.0) / 3.0 + 0.70, 4))
            return RankingPowerSanityDecision(
                status="quarantine",
                confidence=confidence,
                reasons=[
                    "thp_power_outlier",
                    "source_shape_digit_explosion",
                    f"power_to_local_median_ratio:{ratio:.2f}",
                ],
                local_median=local_median,
                local_ratio=ratio,
            )

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
                    "alliance_power_outlier",
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
            thp_source_digit_explosion_powers = _thp_source_digit_explosion_powers(source_rows) if ranking_type == "total_hero_power" else set()
            for source_row_index, row in enumerate(source_rows, start=1):
                if ranking_type == "total_hero_power" and is_first_source:
                    recovered_power, recovery_candidates, recovery_reason = None, [], "first_thp_source_no_recovery"
                else:
                    recovered_power, recovery_candidates, recovery_reason = _recover_context_power(
                        row,
                        ranking_type=ranking_type,
                        source_rows=source_rows,
                        source_powers=source_powers,
                        source_row_index=source_row_index,
                    )
                if recovered_power is None:
                    # Backward safety net for legacy cases with strong intrinsic
                    # rank evidence but too little source context to score a
                    # wider candidate set.
                    legacy_recovered_power = _recover_leading_digit_power(
                        row,
                        ranking_type=ranking_type,
                        source_powers=source_powers,
                        source_row_index=source_row_index,
                    )
                    if legacy_recovered_power is not None:
                        recovered_power = legacy_recovered_power
                        recovery_reason = "legacy_leading_digit_recovery"

                if recovered_power is not None:
                    recovered_row = _apply_recovered_power(
                        row,
                        recovered_power,
                        method=f"{ranking_type}_context_candidate_recovery",
                        candidates=recovery_candidates,
                        decision_reason=recovery_reason,
                    )
                    if ranking_type == "total_hero_power":
                        recovered_row.setdefault("thp_sanity_status", "recovered")
                        recovered_row.setdefault("thp_sanity_confidence", 0.95)
                    guarded.setdefault(key, []).append(recovered_row)
                    continue

                if recovery_candidates:
                    candidate_decision = RankingPowerSanityDecision(
                        status="quarantine",
                        confidence=0.88,
                        reasons=["power_recovery_candidates_ambiguous", recovery_reason],
                        local_median=int(median(source_powers)) if source_powers else None,
                        local_ratio=_safe_ratio(_power(row) or 0, int(median(source_powers)) if source_powers else None),
                    )
                    quarantined_rows.append(
                        _mark_quarantined(
                            row,
                            server=server,
                            ranking_type=ranking_type,
                            decision=candidate_decision,
                            recovery_candidates=recovery_candidates,
                        )
                    )
                    continue

                decision = evaluate_ranking_power_sanity(
                    row,
                    ranking_type=ranking_type,
                    source_powers=source_powers,
                    is_first_source=is_first_source,
                    source_index=source_index,
                    prior_high_value_sources=prior_high_value_sources,
                    source_row_index=source_row_index,
                    source_shape_outlier_powers=source_shape_outlier_powers,
                    thp_source_digit_explosion_powers=thp_source_digit_explosion_powers,
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
