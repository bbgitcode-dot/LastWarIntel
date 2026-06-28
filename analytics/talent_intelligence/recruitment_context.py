"""
Sentinel
Recruitment Context
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RecruitmentContext:
    """
    Input context for calculating the recruitment value
    of an alliance.

    This context intentionally contains only analytical
    input values and no presentation or application models.
    """

    #
    # Core intelligence
    #
    talent_value: float

    structural_health: float

    recruitability: float

    #
    # Roster composition
    #
    whale_density: float = 0.0

    elite_density: float = 0.0

    recruitable_density: float = 0.0

    #
    # Trend analysis
    #
    momentum: float = 0.0