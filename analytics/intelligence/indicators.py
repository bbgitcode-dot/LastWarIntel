"""
Sentinel
Strategic Intelligence Indicators
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class IndicatorLevel(Enum):
    """
    Strategic indicator severity / interpretation.
    """

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class IndicatorScope(Enum):
    """
    Scope an indicator belongs to.
    """

    SERVER = "Server"
    ALLIANCE = "Alliance"
    PLAYER = "Player"
    SYSTEM = "System"


@dataclass(slots=True, frozen=True)
class StrategicIndicator:
    """
    Reusable strategic indicator.

    Indicators are derived from IntelligenceFacts and can be used
    by server, alliance, player and report views.
    """

    title: str

    value: float

    scope: IndicatorScope

    level: IndicatorLevel

    unit: str = ""

    summary: str = ""

    tags: list[str] = field(default_factory=list)