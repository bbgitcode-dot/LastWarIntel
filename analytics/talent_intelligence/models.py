"""
Sentinel
Talent Intelligence Models
"""

from __future__ import annotations

from dataclasses import dataclass, field

from analytics.intelligence.indicators import StrategicIndicator


@dataclass(slots=True, frozen=True)
class TalentMetrics:
    """
    Raw talent statistics for one alliance or server.
    """

    total_players: int

    players_below_180: int
    players_180_plus: int
    players_200_plus: int
    players_250_plus: int
    players_300_plus: int

    below_180_percent: float
    recruitment_efficiency: float
    whale_density: float
    elite_ratio: float

    average_power: float
    median_power: float
    total_power: float
    top5_power: float
    top10_power: float

    top5_concentration: float
    top10_concentration: float
    dependency_index: float

    recruitment_value_score: float


@dataclass(slots=True, frozen=True)
class TalentAssessment:
    """
    Talent assessment.
    """

    metrics: TalentMetrics

    indicators: list[StrategicIndicator] = field(default_factory=list)