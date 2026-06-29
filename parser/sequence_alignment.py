"""Sequence-aware matching helpers for validation and future reconstruction.

The first production use is Ground Truth validation: when exact power matching
fails, Sentinel scores all candidates in the same server by combining recoverable
power, normalized name similarity, alliance compatibility and rank proximity.
This treats a ranking as a sequence instead of isolated rows and prevents a
single shifted OCR rank from poisoning a whole block.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd

from parser.power_normalization import PowerMatchResult, compare_power


@dataclass(frozen=True, slots=True)
class SequenceCandidate:
    row_index: int
    score: float
    power: PowerMatchResult
    name_similarity: float
    alliance_match: bool
    rank_distance: int | None
    method: str


def _rank_factor(expected_rank: int | None, actual_rank: int | None) -> float:
    if expected_rank is None or actual_rank is None:
        return 0.0
    distance = abs(expected_rank - actual_rank)
    if distance == 0:
        return 1.0
    if distance <= 3:
        return 0.75
    if distance <= 10:
        return 0.35
    return 0.0


def find_best_sequence_candidate(
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
    min_score: float = 0.78,
) -> tuple[pd.Series | None, str, SequenceCandidate | None]:
    """Return the strongest sequence-aware candidate or no match.

    The score is intentionally conservative: a recovered power is required for
    strong matches; name/alliance/rank can then disambiguate shifted blocks.
    """
    best: tuple[pd.Series, SequenceCandidate] | None = None

    for row_index, row in candidates.iterrows():
        actual_power = row.get("power")
        actual_name = normalize_name(row.get("ocr_name", row.get("player_name", "")))
        actual_alliance = normalize_tag(row.get("alliance", row.get("alliance_tag", "")))
        actual_rank = row.get("rank")
        try:
            actual_rank_i = int(actual_rank) if pd.notna(actual_rank) else None
        except (TypeError, ValueError):
            actual_rank_i = None

        power_result = compare_power(expected_power, actual_power)
        if not power_result.match:
            continue

        nscore = name_similarity(expected_name, actual_name)
        # Recovered powers are powerful but dangerous if the name clearly does
        # not belong to the same player. Require solid name evidence before a
        # truncated/scaled power can override rank order.
        if power_result.match_type not in {"exact", "near"} and nscore < 0.75:
            continue
        amatch = alliance_match(expected_alliance, actual_alliance)
        rfactor = _rank_factor(expected_rank, actual_rank_i)

        # Recovered power is the row anchor. Name and alliance determine whether
        # the candidate belongs to the same entity. Rank is only weak evidence
        # because rank is exactly the signal that can shift in overlapping lists.
        score = (
            power_result.similarity * 0.56
            + nscore * 0.29
            + (1.0 if amatch else 0.0) * 0.12
            + rfactor * 0.03
        )

        if power_result.match_type in {"exact", "near"}:
            method = "server_power"
        else:
            method = f"sequence_{power_result.match_type}"

        candidate = SequenceCandidate(
            row_index=int(row_index),
            score=round(score, 4),
            power=power_result,
            name_similarity=round(nscore, 4),
            alliance_match=amatch,
            rank_distance=None if expected_rank is None or actual_rank_i is None else abs(expected_rank - actual_rank_i),
            method=method,
        )
        if best is None or candidate.score > best[1].score:
            best = (row, candidate)

    if best is None or best[1].score < min_score:
        return None, "missing", None

    return best[0], best[1].method, best[1]
