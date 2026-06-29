"""Gap recovery helpers for Ground Truth validation.

This module does not invent missing players. It classifies broken stretches in a
ranking sequence so Sentinel can distinguish a real match, a rejected rank
fallback, and a recoverable gap block bounded by reliable anchors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True, slots=True)
class GapBlock:
    start_rank: int | None
    end_rank: int | None
    rows: int
    previous_anchor_rank: int | None
    next_anchor_rank: int | None
    gap_type: str


def _as_bool(value: Any) -> bool:
    return bool(value) if pd.notna(value) else False


def _rank(value: Any) -> int | None:
    try:
        if pd.isna(value):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_valid_anchor(row: pd.Series) -> bool:
    """Reliable anchors are strong enough to bound a gap block."""
    if _as_bool(row.get("bad_match")):
        return False
    if row.get("match_method") == "missing":
        return False
    return _as_bool(row.get("power_match")) and (
        _as_bool(row.get("alliance_match")) or _as_bool(row.get("name_normalized_match"))
    )


def _is_gap_row(row: pd.Series) -> bool:
    method = str(row.get("match_method"))
    return bool(method in {"missing", "blocked_rank_fallback"} or _as_bool(row.get("bad_match")))


def annotate_gap_recovery(detail: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Annotate bad/missing stretches without turning them into matches.

    A gap is considered recoverable when a contiguous bad/missing block is
    bounded by valid anchors on both sides. This is a review signal, not a match.
    """
    if detail.empty:
        metrics = {
            "gap_blocks": 0,
            "gap_rows": 0,
            "recoverable_gap_blocks": 0,
            "recoverable_gap_rows": 0,
            "blocked_rank_fallbacks": 0,
        }
        return detail.copy(), metrics

    annotated = detail.copy().sort_values(["server", "rank"]).reset_index(drop=True)
    annotated["gap_status"] = "ok"
    annotated["gap_block_id"] = ""
    annotated["gap_previous_anchor_rank"] = pd.NA
    annotated["gap_next_anchor_rank"] = pd.NA
    annotated["gap_recoverable"] = False
    annotated["gap_reason"] = ""

    blocks: list[GapBlock] = []
    block_id = 0

    for server, server_df in annotated.groupby("server", sort=False):
        indices = list(server_df.index)
        gap_run: list[int] = []

        def flush_run(run: list[int]) -> None:
            nonlocal block_id
            if not run:
                return
            first = run[0]
            last = run[-1]
            prev_anchor = None
            next_anchor = None
            for idx in reversed(indices[: indices.index(first)]):
                if _is_valid_anchor(annotated.loc[idx]):
                    prev_anchor = _rank(annotated.loc[idx, "rank"])
                    break
            for idx in indices[indices.index(last) + 1 :]:
                if _is_valid_anchor(annotated.loc[idx]):
                    next_anchor = _rank(annotated.loc[idx, "rank"])
                    break

            recoverable = prev_anchor is not None and next_anchor is not None
            gap_type = "bounded_gap" if recoverable else "unbounded_gap"
            block_label = f"{server}:{block_id}"
            block_id += 1

            for idx in run:
                method = str(annotated.loc[idx, "match_method"])
                if method == "missing":
                    status = "missing_entry"
                elif method == "blocked_rank_fallback" or method.startswith("bad_"):
                    status = "blocked_rank_fallback"
                else:
                    status = "gap_row"
                annotated.loc[idx, "gap_status"] = status
                annotated.loc[idx, "gap_block_id"] = block_label
                annotated.loc[idx, "gap_previous_anchor_rank"] = prev_anchor
                annotated.loc[idx, "gap_next_anchor_rank"] = next_anchor
                annotated.loc[idx, "gap_recoverable"] = recoverable
                annotated.loc[idx, "gap_reason"] = gap_type

            blocks.append(
                GapBlock(
                    start_rank=_rank(annotated.loc[first, "rank"]),
                    end_rank=_rank(annotated.loc[last, "rank"]),
                    rows=len(run),
                    previous_anchor_rank=prev_anchor,
                    next_anchor_rank=next_anchor,
                    gap_type=gap_type,
                )
            )

        for idx in indices:
            row = annotated.loc[idx]
            if _is_gap_row(row):
                gap_run.append(idx)
            else:
                flush_run(gap_run)
                gap_run = []
        flush_run(gap_run)

    gap_rows = int((annotated["gap_status"] != "ok").sum())
    recoverable_rows = int(annotated["gap_recoverable"].sum())
    metrics = {
        "gap_blocks": len(blocks),
        "gap_rows": gap_rows,
        "recoverable_gap_blocks": sum(1 for block in blocks if block.gap_type == "bounded_gap"),
        "recoverable_gap_rows": recoverable_rows,
        "blocked_rank_fallbacks": int((annotated["gap_status"] == "blocked_rank_fallback").sum()),
    }
    return annotated, metrics
