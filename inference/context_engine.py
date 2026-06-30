"""Context Engine for explainable validation inference.

This module is intentionally read-only with respect to Operational Truth. It
works on validation detail rows after Guard/Gap annotations have made uncertainty
explicit. The first use case is a bounded local ranking gap where the observed
export has no safe row-level match, but neighboring trusted anchors make the
missing position explainable.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

import pandas as pd


@dataclass(frozen=True, slots=True)
class ContextInference:
    row_index: int
    rank: int | None
    method: str
    confidence: float
    decision: str
    evidence: str
    previous_anchor_rank: int | None
    next_anchor_rank: int | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _as_int(value: Any) -> int | None:
    try:
        if pd.isna(value):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_bool(value: Any) -> bool:
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    return bool(value)


def _is_trusted_anchor(row: pd.Series) -> bool:
    if not _as_bool(row.get("valid_match")):
        return False
    if str(row.get("match_method", "")).startswith("inference_"):
        return False
    return _as_bool(row.get("power_match")) and (
        _as_bool(row.get("alliance_match")) or _as_bool(row.get("name_normalized_match"))
    )


def _power_between(candidate_power: int | None, previous_power: int | None, next_power: int | None) -> bool:
    if candidate_power is None or previous_power is None or next_power is None:
        return False
    upper = max(previous_power, next_power)
    lower = min(previous_power, next_power)
    return lower >= candidate_power or candidate_power >= upper if False else lower <= candidate_power <= upper


def _confidence(*, row: pd.Series, previous: pd.Series, next_row: pd.Series) -> tuple[float, list[str]]:
    evidence: list[str] = []
    score = 0.0

    previous_rank = _as_int(previous.get("rank"))
    current_rank = _as_int(row.get("rank"))
    next_rank = _as_int(next_row.get("rank"))
    if previous_rank is not None and current_rank is not None and next_rank is not None:
        if previous_rank < current_rank < next_rank:
            score += 0.30
            evidence.append("rank_between_trusted_neighbors")
        if next_rank - previous_rank <= 3:
            score += 0.16
            evidence.append("tight_bounded_gap")

    if _power_between(
        _as_int(row.get("expected_power")),
        _as_int(previous.get("expected_power")),
        _as_int(next_row.get("expected_power")),
    ):
        score += 0.30
        evidence.append("expected_power_fits_neighbor_trend")

    if _as_bool(row.get("gap_recoverable")):
        score += 0.14
        evidence.append("gap_marked_recoverable_by_validator")

    if str(row.get("match_method", "")) in {"blocked_rank_fallback", "missing"}:
        score += 0.10
        evidence.append("unsafe_row_match_blocked")

    return round(min(score, 0.99), 4), evidence


def apply_contextual_inference(detail: pd.DataFrame, min_confidence: float = 0.88) -> tuple[pd.DataFrame, list[ContextInference]]:
    """Apply read-only contextual inference to validation detail rows.

    Accepted inferences are explicitly marked with ``match_method`` starting
    with ``inference_``. They are not OCR matches and do not alter raw OCR
    columns; reports can therefore distinguish observed matches from derived
    conclusions.
    """
    if detail.empty:
        return detail.copy(), []

    inferred = detail.copy().sort_values(["server", "rank"]).reset_index(drop=True)
    if "inference_status" not in inferred.columns:
        inferred["inference_status"] = "not_evaluated"
        inferred["inference_confidence"] = 0.0
        inferred["inference_evidence"] = ""
        inferred["inference_decision"] = ""

    # Ensure valid_match exists for anchor checks even if caller runs inference
    # before final metric calculation.
    if "valid_match" not in inferred.columns:
        inferred["valid_match"] = (~inferred["match_method"].isin(["missing", "blocked_rank_fallback"])) & (~inferred["bad_match"])

    accepted: list[ContextInference] = []
    for server, server_df in inferred.groupby("server", sort=False):
        indices = list(server_df.index)
        for idx in indices:
            row = inferred.loc[idx]
            if str(row.get("match_method", "")) not in {"blocked_rank_fallback", "missing"}:
                continue
            if not _as_bool(row.get("gap_recoverable")):
                inferred.loc[idx, "inference_status"] = "not_recoverable"
                continue

            prev_idx = None
            next_idx = None
            for candidate_idx in reversed(indices[: indices.index(idx)]):
                if _is_trusted_anchor(inferred.loc[candidate_idx]):
                    prev_idx = candidate_idx
                    break
            for candidate_idx in indices[indices.index(idx) + 1 :]:
                if _is_trusted_anchor(inferred.loc[candidate_idx]):
                    next_idx = candidate_idx
                    break
            if prev_idx is None or next_idx is None:
                inferred.loc[idx, "inference_status"] = "insufficient_anchors"
                continue

            previous = inferred.loc[prev_idx]
            next_row = inferred.loc[next_idx]
            confidence, evidence = _confidence(row=row, previous=previous, next_row=next_row)
            inferred.loc[idx, "inference_confidence"] = confidence
            inferred.loc[idx, "inference_evidence"] = ";".join(evidence)

            if confidence >= min_confidence:
                method = "inference_context_gap"
                inferred.loc[idx, "match_method"] = method
                inferred.loc[idx, "failure_class"] = "inferred_context_gap"
                inferred.loc[idx, "inference_status"] = "accepted"
                inferred.loc[idx, "inference_decision"] = "accepted_read_only_contextual_inference"
                inference = ContextInference(
                    row_index=int(idx),
                    rank=_as_int(row.get("rank")),
                    method=method,
                    confidence=confidence,
                    decision="accepted",
                    evidence=";".join(evidence),
                    previous_anchor_rank=_as_int(previous.get("rank")),
                    next_anchor_rank=_as_int(next_row.get("rank")),
                )
                accepted.append(inference)
            else:
                inferred.loc[idx, "inference_status"] = "rejected_low_confidence"
                inferred.loc[idx, "inference_decision"] = "rejected"

    return inferred, accepted
