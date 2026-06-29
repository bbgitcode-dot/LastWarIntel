"""Gap resolver helpers for cross-screenshot / cross-server OCR leakage.

Some Last War ranking screenshots are captured around scroll boundaries. When the
server metadata on one screenshot is misread, valid rows can land in a neighbouring
server sheet (for example 551 rows exported under 552). The resolver is deliberately
conservative: it only pulls a candidate across server boundaries when strong row
evidence exists, primarily power plus name/alliance compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd

from parser.power_normalization import PowerMatchResult, compare_power


@dataclass(frozen=True, slots=True)
class GapResolutionCandidate:
    row_index: int
    score: float
    power: PowerMatchResult
    name_similarity: float
    alliance_match: bool
    source_server: int | None
    method: str


def _as_int(value: Any) -> int | None:
    try:
        if pd.isna(value):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def find_cross_server_gap_candidate(
    *,
    expected_server: int | None,
    expected_rank: int | None,
    expected_power: int | None,
    expected_name: str,
    expected_alliance: str,
    all_candidates: pd.DataFrame,
    normalize_name: Callable[[Any], str],
    normalize_tag: Callable[[Any], str],
    name_similarity: Callable[[str, str], float],
    alliance_match: Callable[[str, str], bool],
    min_score: float = 0.82,
) -> tuple[pd.Series | None, str, GapResolutionCandidate | None]:
    """Find a high-confidence candidate outside the expected server bucket.

    This is a gap repair, not a general fallback. It is intentionally strict so
    it does not hide real data loss behind speculative matches.
    """
    if all_candidates.empty:
        return None, "missing", None

    expected_server_i = _as_int(expected_server)
    pool = all_candidates.copy()
    if expected_server_i is not None and "server" in pool.columns:
        pool = pool[pool["server"].map(_as_int) != expected_server_i]
    if pool.empty:
        return None, "missing", None

    best: tuple[pd.Series, GapResolutionCandidate] | None = None
    for row_index, row in pool.iterrows():
        actual_power = row.get("power")
        power_result = compare_power(expected_power, actual_power)
        if not power_result.match:
            continue

        actual_name = normalize_name(row.get("ocr_name", row.get("player_name", "")))
        actual_alliance = normalize_tag(row.get("alliance", row.get("alliance_tag", "")))
        nscore = name_similarity(expected_name, actual_name)
        amatch = alliance_match(expected_alliance, actual_alliance)

        # Exact/recovered power is necessary but not sufficient. The row must
        # also carry identity evidence so a wrong-server correction remains
        # explainable.
        if not (nscore >= 0.72 or (amatch and nscore >= 0.45)):
            continue

        power_weight = 0.62 if power_result.match_type in {"exact", "near"} else 0.56
        score = (
            power_result.similarity * power_weight
            + nscore * 0.28
            + (1.0 if amatch else 0.0) * 0.10
        )

        candidate = GapResolutionCandidate(
            row_index=int(row_index),
            score=round(score, 4),
            power=power_result,
            name_similarity=round(nscore, 4),
            alliance_match=amatch,
            source_server=_as_int(row.get("server")),
            method=f"gap_cross_server_{power_result.match_type}",
        )
        if best is None or candidate.score > best[1].score:
            best = (row, candidate)

    if best is None or best[1].score < min_score:
        return None, "missing", None
    return best[0], best[1].method, best[1]
