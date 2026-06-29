"""Power normalization and recovery helpers for OCR damaged THP values.

Last War THP values are strong row anchors, but OCR sometimes drops the last
or middle digit when the value is captured near UI decoration. This module does
not blindly rewrite production data. It exposes deterministic comparison helpers
that can explain whether two power values are exact, near, scaled/truncated, or
unrelated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class PowerMatchResult:
    expected: int | None
    actual: int | None
    recovered_actual: int | None
    match: bool
    match_type: str
    similarity: float
    correction: str | None = None


def _as_int(value: int | float | str | None) -> int | None:
    if value is None:
        return None
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _relative_similarity(expected: int, actual: int) -> float:
    if expected <= 0 or actual <= 0:
        return 0.0
    diff = abs(expected - actual) / max(expected, actual)
    return max(0.0, 1.0 - diff)


def _candidate_repairs(actual: int) -> Iterable[tuple[int, str]]:
    """Generate conservative OCR power repair candidates.

    The most common observed damage is an 8-digit value that should be a
    9-digit THP value. Multiplying by 10 restores the approximate magnitude and
    allows strict similarity scoring without inventing exact missing digits.
    """
    yield actual, "exact"

    digits = str(actual)
    if 7 <= len(digits) <= 8:
        yield actual * 10, "scale_x10_truncated_digit"
        # OCR occasionally drops a zero in dense values. Re-inserting a zero at
        # each internal position is still deterministic and bounded.
        for index in range(1, len(digits)):
            yield int(digits[:index] + "0" + digits[index:]), "insert_zero"


def compare_power(
    expected: int | float | str | None,
    actual: int | float | str | None,
    *,
    near_tolerance_ratio: float = 0.00001,
    recovered_tolerance_ratio: float = 0.005,
) -> PowerMatchResult:
    """Compare two THP values and explain the match quality."""
    expected_i = _as_int(expected)
    actual_i = _as_int(actual)
    if expected_i is None or actual_i is None:
        return PowerMatchResult(expected_i, actual_i, None, False, "missing", 0.0)

    if expected_i == actual_i:
        return PowerMatchResult(expected_i, actual_i, actual_i, True, "exact", 1.0)

    direct_similarity = _relative_similarity(expected_i, actual_i)
    direct_diff = abs(expected_i - actual_i) / max(expected_i, actual_i)
    if direct_diff <= near_tolerance_ratio:
        return PowerMatchResult(expected_i, actual_i, actual_i, True, "near", direct_similarity)

    best_value = actual_i
    best_type = "mismatch"
    best_similarity = direct_similarity
    for candidate, repair_type in _candidate_repairs(actual_i):
        similarity = _relative_similarity(expected_i, candidate)
        if similarity > best_similarity:
            best_value = candidate
            best_type = repair_type
            best_similarity = similarity

    recovered_diff = abs(expected_i - best_value) / max(expected_i, best_value)
    if best_type != "mismatch" and recovered_diff <= recovered_tolerance_ratio:
        return PowerMatchResult(
            expected_i,
            actual_i,
            best_value,
            True,
            best_type,
            best_similarity,
            correction=f"{actual_i}->{best_value}",
        )

    return PowerMatchResult(expected_i, actual_i, best_value, False, best_type, best_similarity)
