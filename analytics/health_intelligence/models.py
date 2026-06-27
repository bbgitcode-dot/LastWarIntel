"""
Sentinel
Health Intelligence Models
"""

from __future__ import annotations

from dataclasses import dataclass, field

from analytics.intelligence.indicators import StrategicIndicator


@dataclass(slots=True, frozen=True)
class HealthSignal:
    """
    Represents one structural health signal.
    """

    title: str
    impact: int
    confidence: float
    reason: str
    payload: dict


@dataclass(slots=True, frozen=True)
class HealthAssessment:
    """
    Result of structural health analysis.
    """

    score: int

    signals: list[HealthSignal] = field(default_factory=list)

    indicators: list[StrategicIndicator] = field(default_factory=list)