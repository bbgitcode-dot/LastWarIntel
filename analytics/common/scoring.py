"""
LastWarIntel
Scoring Utilities
Version: 1.0
"""

from __future__ import annotations


def average_confidence(values: list[float]) -> float:
    """
    Calculates the average confidence.
    """

    if not values:
        return 0.0

    return sum(values) / len(values)


def weighted_score(
    score: float,
    confidence: float,
) -> float:
    """
    Combines score and confidence.
    """

    return score * (confidence / 100.0)