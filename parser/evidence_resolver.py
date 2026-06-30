"""Evidence-based recovery helpers for bounded Ground Truth gaps.

The resolver is not part of OCR and it does not change Operational Truth.
It is a validation/inference helper: when the normal sequence matcher refuses a
rank fallback, the validator can still ask whether there is a unique row in the
same trusted export whose observed evidence is strong enough to explain the gap.

This deliberately separates "observed" from "inferred": the original OCR row is
kept unchanged, while the validation report records the recovery method and
confidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd

from parser.power_normalization import PowerMatchResult, compare_power


@dataclass(frozen=True, slots=True)
class EvidenceResolutionCandidate:
    row_index: int
    score: float
    power: PowerMatchResult
    name_similarity: float
    alliance_match: bool
    rank_distance: int | None
    method: str
    evidence: str


def _as_int(value: Any) -> int | None:
    try:
        if pd.isna(value):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _rank_distance(expected_rank: int | None, actual_rank: Any) -> int | None:
    actual_rank_i = _as_int(actual_rank)
    if expected_rank is None or actual_rank_i is None:
        return None
    return abs(int(expected_rank) - actual_rank_i)


def _score_candidate(
    *,
    power_result: PowerMatchResult,
    name_similarity_value: float,
    alliance_matches: bool,
    rank_distance: int | None,
) -> float:
    rank_score = 0.0
    if rank_distance is not None:
        if rank_distance == 0:
            rank_score = 1.0
        elif rank_distance <= 3:
            rank_score = 0.65
        elif rank_distance <= 10:
            rank_score = 0.25

    power_weight = 0.72 if power_result.match_type == "exact" else 0.62
    return round(
        power_result.similarity * power_weight
        + name_similarity_value * 0.18
        + (1.0 if alliance_matches else 0.0) * 0.07
        + rank_score * 0.03,
        4,
    )


def find_same_server_evidence_candidate(
    *,
    expected_rank: int | None,
    expected_power: int | None,
    expected_name: str,
    expected_alliance: str,
    candidates: pd.DataFrame,
    normalize_name: Callable[[Any], str],
    normalize_tag: Callable[[Any], str],
    name_similarity: Callable[[str, str], float],
    alliance_match: Callable[[str, str], bool],
    min_score: float = 0.72,
) -> tuple[pd.Series | None, str, EvidenceResolutionCandidate | None]:
    """Return a unique evidence-backed same-server candidate.

    Rules:
    - Exact power is accepted only when unique in the scoped server export. This
      captures rows such as UNKNOWN-name entries where the value itself is the
      trustworthy row anchor.
    - Near/recovered power needs additional identity evidence. This prevents a
      fuzzy power repair from becoming a disguised rank fallback.
    - The returned method starts with ``gap_`` so downstream reports count it as
      a resolved recoverable gap, not as a normal OCR match.
    """
    if candidates.empty or expected_power is None:
        return None, "missing", None

    exact_matches: list[tuple[int, pd.Series, PowerMatchResult, float, bool, int | None]] = []
    fuzzy_matches: list[tuple[int, pd.Series, PowerMatchResult, float, bool, int | None]] = []

    for row_index, row in candidates.iterrows():
        actual_power = row.get("power")
        exact_power = compare_power(expected_power, actual_power)
        relaxed_power = compare_power(
            expected_power,
            actual_power,
            near_tolerance_ratio=0.00005,
            recovered_tolerance_ratio=0.005,
        )
        power_result = exact_power if exact_power.match else relaxed_power
        if not power_result.match:
            continue

        actual_name = normalize_name(row.get("ocr_name", row.get("player_name", "")))
        actual_alliance = normalize_tag(row.get("alliance", row.get("alliance_tag", "")))
        nscore = name_similarity(expected_name, actual_name)
        amatch = alliance_match(expected_alliance, actual_alliance)
        distance = _rank_distance(expected_rank, row.get("rank"))
        payload = (int(row_index), row, power_result, nscore, amatch, distance)
        if power_result.match_type == "exact":
            exact_matches.append(payload)
        elif nscore >= 0.55 or amatch:
            fuzzy_matches.append(payload)

    # Exact power is the strongest observed row anchor, but only if it is unique.
    if len(exact_matches) == 1:
        row_index, row, power_result, nscore, amatch, distance = exact_matches[0]
        score = _score_candidate(
            power_result=power_result,
            name_similarity_value=nscore,
            alliance_matches=amatch,
            rank_distance=distance,
        )
        if score >= min_score:
            candidate = EvidenceResolutionCandidate(
                row_index=row_index,
                score=score,
                power=power_result,
                name_similarity=round(nscore, 4),
                alliance_match=amatch,
                rank_distance=distance,
                method="gap_same_server_exact_power",
                evidence="unique_exact_power",
            )
            return row, candidate.method, candidate

    # Fuzzy power is useful only with identity support and clear best candidate.
    if fuzzy_matches:
        scored: list[tuple[float, tuple[int, pd.Series, PowerMatchResult, float, bool, int | None]]] = []
        for payload in fuzzy_matches:
            _row_index, _row, power_result, nscore, amatch, distance = payload
            score = _score_candidate(
                power_result=power_result,
                name_similarity_value=nscore,
                alliance_matches=amatch,
                rank_distance=distance,
            )
            scored.append((score, payload))
        scored.sort(key=lambda item: item[0], reverse=True)
        best_score, best_payload = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else 0.0
        if best_score >= min_score and best_score - second_score >= 0.05:
            row_index, row, power_result, nscore, amatch, distance = best_payload
            candidate = EvidenceResolutionCandidate(
                row_index=row_index,
                score=best_score,
                power=power_result,
                name_similarity=round(nscore, 4),
                alliance_match=amatch,
                rank_distance=distance,
                method=f"gap_same_server_{power_result.match_type}",
                evidence="fuzzy_power_with_identity",
            )
            return row, candidate.method, candidate

    return None, "missing", None
