"""
LastWarIntel
Ranking Models
Version: 1.0

Domain models for strategic rankings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RankingType(Enum):
    RECRUITMENT = "Recruitment"
    GROWTH = "Growth"
    HEALTH = "Health"
    RISK = "Risk"
    RECOVERY = "Recovery"


@dataclass(slots=True, frozen=True)
class RankingEntry:
    """
    One ranked alliance.
    """

    alliance: str

    score: float

    title: str

    summary: str

    confidence: float


@dataclass(slots=True, frozen=True)
class Ranking:
    """
    One complete ranking.
    """

    ranking_type: RankingType

    entries: list[RankingEntry] = field(default_factory=list)