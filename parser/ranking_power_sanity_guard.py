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
    digit_preservation_score: float = 0.0


def _candidate_dict(candidate: PowerRecoveryCandidate) -> dict[str, Any]:
    return {
        "value": candidate.value,
        "score": round(candidate.score, 4),
        "reasons": list(candidate.reasons),
        "digit_preservation_score": round(candidate.digit_preservation_score, 4),
    }



def _common_prefix_length(left: str, right: str) -> int:
    count = 0
    for a, b in zip(left, right):
        if a != b:
            break
        count += 1
    return count


def _common_suffix_length(left: str, right: str) -> int:
    count = 0
    for a, b in zip(reversed(left), reversed(right)):
        if a != b:
            break
        count += 1
    return count


def _digit_preservation_score(observed: int, candidate: int) -> float:
    """Score how well a recovery candidate preserves visible OCR digits.

    Context decides whether a value is plausible, but OCR recovery should still
    prefer candidates that keep the observed digit evidence in-place. This avoids
    low-truncation false recoveries such as 32030601 -> 302030601 when the
    candidate 320306010 preserves the visible leading sequence more faithfully.
    """
    source = str(observed)
    target = str(candidate)
    if not source or not target:
        return 0.0

    prefix = _common_prefix_length(source, target) / max(len(source), 1)
    suffix = _common_suffix_length(source, target) / max(len(source), 1)

    # Subsequence preservation catches insert-zero candidates without rewarding
    # arbitrary reshuffles.
    cursor = 0
    matched = 0
    for digit in target:
        if cursor < len(source) and digit == source[cursor]:
            cursor += 1
            matched += 1
    subsequence = matched / max(len(source), 1)

    score = (0.48 * prefix) + (0.32 * suffix) + (0.20 * subsequence)

    if target.startswith(source):
        score += 0.16
    if target.startswith(source[:3]) and target.endswith(source[-4:]):
        score += 0.14
    if len(target) == len(source) + 1 and target.replace("0", "", 1) == source:
        score += 0.08

    return round(min(1.0, max(0.0, score)), 6)


def _source_low_powers_for_recovery(*, ranking_type: str, source_powers: list[int], observed: int) -> list[int]:
    if ranking_type == "total_hero_power":
        return [power for power in source_powers if 50_000_000 <= power < min(observed, 350_000_000)]
    if ranking_type == "alliance_power":
        return [power for power in source_powers if 500_000_000 <= power < min(observed, 45_000_000_000)]
    return []


def _source_normal_powers_for_low_recovery(*, ranking_type: str, source_powers: list[int], observed: int) -> list[int]:
    """Return source-local normal powers for low/truncated OCR candidates."""
    if ranking_type == "total_hero_power":
        return [power for power in source_powers if max(80_000_000, observed * 3) <= power <= 500_000_000]
    return []


def _looks_like_low_truncation_candidate(*, ranking_type: str, observed: int, source_powers: list[int]) -> bool:
    if ranking_type != "total_hero_power":
        return False
    if not (1_000_000 <= observed < 50_000_000):
        return False
    normal_values = _source_normal_powers_for_low_recovery(
        ranking_type=ranking_type,
        source_powers=source_powers,
        observed=observed,
    )
    if len(normal_values) < 2:
        return False
    local_median = int(median(normal_values))
    return local_median / max(observed, 1) >= 3.0


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

    values: set[int] = set()

    if (
        ranking_type == "total_hero_power"
        and _looks_like_low_truncation_candidate(
            ranking_type=ranking_type,
            observed=observed,
            source_powers=source_powers,
        )
    ):
        for multiplier in (10, 100):
            candidate = observed * multiplier
            if 80_000_000 <= candidate <= 500_000_000:
                values.add(candidate)
        for index in range(1, len(text)):
            candidate = int(text[:index] + "0" + text[index:])
            if 80_000_000 <= candidate <= 500_000_000:
                values.add(candidate)

    if len(text) < 8 or text[0] not in {"7", "8"}:
        return sorted(values)

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
    text = str(observed)

    is_low_truncation = _looks_like_low_truncation_candidate(
        ranking_type=ranking_type,
        observed=observed,
        source_powers=source_powers,
    )

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
            recovered_context = (
                _source_normal_powers_for_low_recovery(ranking_type=ranking_type, source_powers=[power], observed=observed)
                if is_low_truncation
                else _source_low_powers_for_recovery(ranking_type=ranking_type, source_powers=[power], observed=observed)
            )
            if context_rank < row_rank:
                prior_lows.extend(recovered_context)
            elif context_rank > row_rank:
                following_lows.extend(recovered_context)
    elif index is not None:
        for prior in source_rows[:index]:
            power = _power(prior)
            if power is not None:
                prior_lows.extend(
                    _source_normal_powers_for_low_recovery(ranking_type=ranking_type, source_powers=[power], observed=observed)
                    if is_low_truncation
                    else _source_low_powers_for_recovery(ranking_type=ranking_type, source_powers=[power], observed=observed)
                )
        for following in source_rows[index + 1:]:
            power = _power(following)
            if power is not None:
                following_lows.extend(
                    _source_normal_powers_for_low_recovery(ranking_type=ranking_type, source_powers=[power], observed=observed)
                    if is_low_truncation
                    else _source_low_powers_for_recovery(ranking_type=ranking_type, source_powers=[power], observed=observed)
                )

    low_values = (
        _source_normal_powers_for_low_recovery(ranking_type=ranking_type, source_powers=source_powers, observed=observed)
        if is_low_truncation
        else _source_low_powers_for_recovery(ranking_type=ranking_type, source_powers=source_powers, observed=observed)
    )
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

        digit_preservation = _digit_preservation_score(observed, value) if is_low_truncation else 0.0

        if is_low_truncation:
            if digit_preservation:
                score += digit_preservation * 0.24
                reasons.append(f"digit_preservation:{digit_preservation:.3f}")
            if value == observed * 10:
                score += 0.22
                reasons.append("ocr_error_model:scale_x10_truncated_digit")
            elif value == observed * 100:
                score += 0.18
                reasons.append("ocr_error_model:scale_x100_truncated_digit")
            elif str(value).replace("0", "", 1) == text:
                score += 0.18
                reasons.append("ocr_error_model:insert_zero")
            else:
                score += 0.06
                reasons.append("ocr_error_model:low_truncation_candidate")
        elif ranking_type == "total_hero_power" and 500_000_000 <= observed < 1_000_000_000:
            value_text = str(value)
            if len(value_text) == len(text) and value_text[1:] == text[1:]:
                if value_text[0] == "1":
                    score += 0.14
                    reasons.append("ocr_error_model:leading_digit_to_1")
                elif value_text[0] == "2":
                    score += 0.06
                    reasons.append("ocr_error_model:leading_digit_to_2")
                elif value_text[0] == "3":
                    score += 0.03
                    reasons.append("ocr_error_model:leading_digit_to_3")

        # Small penalty for candidates that remain too close to the observed OCR
        # explosion, because they likely preserve the false leading magnitude.
        if not is_low_truncation and value >= observed * 0.50:
            score -= 0.12
            reasons.append("too_close_to_observed_explosion")

        digit_preservation = _digit_preservation_score(observed, value)
        candidates.append(PowerRecoveryCandidate(
            value=value,
            score=round(score, 6),
            reasons=reasons,
            digit_preservation_score=digit_preservation,
        ))

    candidates.sort(key=lambda candidate: (candidate.score, -abs(candidate.value - (low_median or candidate.value))), reverse=True)
    return candidates


def _candidate_order_strength(candidate: PowerRecoveryCandidate) -> int:
    """Return a small, explainable segment-order score for a candidate.

    v0.9.5.52 uses this only as a tie-breaker.  Context scoring can produce
    near-ties for 7xxM rows where one candidate is slightly closer to the local
    median but another candidate preserves the visible rank segment order.  We
    prefer the order-consistent candidate only when scores are already close.
    """
    strength = 0
    for reason in candidate.reasons:
        if reason.startswith("fits_prior_neighbour_order") or reason.startswith("fits_following_neighbour_order"):
            strength += 2
        elif reason.startswith("near_prior_neighbour") or reason.startswith("near_following_neighbour"):
            strength += 1
        elif reason.startswith("breaks_prior_neighbour_order") or reason.startswith("breaks_following_neighbour_order"):
            strength -= 3
    return strength


def _has_order_break(candidate: PowerRecoveryCandidate) -> bool:
    return any(reason.startswith("breaks_") for reason in candidate.reasons)


def _candidate_method(candidate: PowerRecoveryCandidate) -> str:
    for reason in candidate.reasons:
        if reason.startswith("ocr_error_model:"):
            return reason.split(":", 1)[1]
    return ""


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

    is_low_truncation = _looks_like_low_truncation_candidate(
        ranking_type=ranking_type,
        observed=_power(row) or 0,
        source_powers=source_powers,
    )

    if is_low_truncation:
        # Low-truncation was the main risk introduced in .50/.51: it improved
        # recall, but it can turn a row-gap into a confident false recovery.
        # Keep single-candidate scale recoveries, but require a stronger margin
        # when multiple digit-preserving candidates compete.
        high_digit_alternative = any(
            candidate is not best and candidate.digit_preservation_score >= 0.84
            for candidate in candidates
        )
        if best.digit_preservation_score < 0.80 and high_digit_alternative:
            return None, candidates, (
                f"segment_digit_conflict:best={best.score:.3f};"
                f"margin={margin:.3f};digit={best.digit_preservation_score:.3f}"
            )
        if len(candidates) == 1 and best.score >= 0.75 and best.digit_preservation_score >= 0.80:
            return best.value, candidates, (
                f"selected_single_digit_preserving_candidate:score={best.score:.3f};"
                f"digit={best.digit_preservation_score:.3f}"
            )
        if (
            _candidate_method(best) == "scale_x10_truncated_digit"
            and not _has_order_break(best)
            and best.score >= 1.00
            and margin >= 0.035
            and best.digit_preservation_score >= 0.80
        ):
            return best.value, candidates, (
                f"selected_segment_consistent_scale_candidate:score={best.score:.3f};"
                f"margin={margin:.3f};digit={best.digit_preservation_score:.3f}"
            )
        if best.score >= 0.75 and margin >= 0.05 and best.digit_preservation_score >= 0.80:
            return best.value, candidates, (
                f"selected_digit_preserving_candidate:score={best.score:.3f};"
                f"margin={margin:.3f};digit={best.digit_preservation_score:.3f}"
            )
        return None, candidates, f"ambiguous_low_truncation_candidates:best={best.score:.3f};margin={margin:.3f}"

    # Segment-order tie-breaker for high OCR explosions.  This recovers rows
    # that .51 quarantined because the OCR error-model and the local median
    # disagreed by only ~0.02, while the second candidate preserved the visible
    # rank segment ordering.  The guard remains conservative: no order-breaker is
    # promoted and candidates must be close in absolute value and score.
    if ranking_type == "total_hero_power" and len(candidates) > 1 and margin < 0.05:
        scale = 1_000_000
        best_order = _candidate_order_strength(best)
        for candidate in candidates[1:]:
            if candidate.score < best.score - 0.055:
                continue
            if abs(candidate.value - best.value) > 2 * scale:
                continue
            if _has_order_break(candidate):
                continue
            if _candidate_order_strength(candidate) >= best_order + 1 and candidate.score >= 0.65:
                return candidate.value, candidates, (
                    f"selected_segment_order_candidate:score={candidate.score:.3f};"
                    f"margin={best.score - candidate.score:.3f};"
                    f"order={_candidate_order_strength(candidate)}>{best_order}"
                )

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


# v0.9.5.49 intentionally removes the old leading-digit recovery decision path. v0.9.5.52 adds segment-order tie-breaks and conservative low-truncation acceptance to the same decision engine.
# Leading-digit transforms may still contribute candidate values, but no row may
# be recovered unless the context candidate decision engine selects a clear
# winner. Ambiguous candidates are quarantined for review.


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
        candidate_dicts = [_candidate_dict(candidate) for candidate in candidates]
        recovered["power_recovery_candidates"] = candidate_dicts
        selected = next((candidate for candidate in candidates if candidate.value == recovered_power), candidates[0])
        second = next((candidate for candidate in candidates if candidate.value != selected.value), None)
        margin = selected.score - (second.score if second else 0.0)
        recovered["power_recovery_selected_score"] = round(selected.score, 4)
        recovered["power_recovery_selected_reason"] = decision_reason or ";".join(selected.reasons)
        recovered["power_recovery_status"] = "recovered"
        recovered["power_recovery_decision_version"] = "v0.9.5.52"
        recovered["power_recovery_decision_strategy"] = "context_candidate_margin"
        recovered["power_recovery_legacy_used"] = False
        recovered["power_candidate_count"] = len(candidates)
        recovered["power_candidate_best"] = selected.value
        recovered["power_candidate_best_score"] = round(selected.score, 4)
        recovered["power_candidate_second"] = second.value if second else None
        recovered["power_candidate_second_score"] = round(second.score, 4) if second else None
        recovered["power_candidate_margin"] = round(margin, 4)
        recovered["power_sanity_confidence"] = min(0.99, max(0.50, round(selected.score, 4)))
    else:
        recovered["power_recovery_status"] = "recovered"
        recovered["power_recovery_decision_version"] = "v0.9.5.52"
        recovered["power_recovery_decision_strategy"] = "context_candidate_margin"
        recovered["power_recovery_legacy_used"] = False
        recovered["power_candidate_count"] = 0
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
        candidates = sorted(recovery_candidates, key=lambda candidate: candidate.score, reverse=True)
        best = candidates[0]
        second = candidates[1] if len(candidates) > 1 else None
        margin = best.score - (second.score if second else 0.0)
        quarantined["power_recovery_candidates"] = [_candidate_dict(candidate) for candidate in candidates]
        quarantined["power_recovery_selected_reason"] = "quarantined_ambiguous_candidates"
        quarantined["power_recovery_status"] = "ambiguous"
        quarantined["power_recovery_decision_version"] = "v0.9.5.52"
        quarantined["power_recovery_decision_strategy"] = "context_candidate_margin"
        quarantined["power_recovery_legacy_used"] = False
        quarantined["power_candidate_count"] = len(candidates)
        quarantined["power_candidate_best"] = best.value
        quarantined["power_candidate_best_score"] = round(best.score, 4)
        quarantined["power_candidate_second"] = second.value if second else None
        quarantined["power_candidate_second_score"] = round(second.score, 4) if second else None
        quarantined["power_candidate_margin"] = round(margin, 4)
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
    """Recover only clear candidate winners and quarantine ambiguous outliers."""
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
                value_for_recovery = _power(row)
                first_source_recovery_blocked = (
                    ranking_type == "total_hero_power"
                    and is_first_source
                    and value_for_recovery not in thp_source_digit_explosion_powers
                    and not (
                        value_for_recovery is not None
                        and _looks_like_low_truncation_candidate(
                            ranking_type=ranking_type,
                            observed=value_for_recovery,
                            source_powers=source_powers,
                        )
                    )
                )
                if first_source_recovery_blocked:
                    recovered_power, recovery_candidates, recovery_reason = None, [], "first_thp_source_no_recovery"
                else:
                    recovered_power, recovery_candidates, recovery_reason = _recover_context_power(
                        row,
                        ranking_type=ranking_type,
                        source_rows=source_rows,
                        source_powers=source_powers,
                        source_row_index=source_row_index,
                    )
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
