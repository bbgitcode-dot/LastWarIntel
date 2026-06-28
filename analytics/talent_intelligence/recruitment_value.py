"""
Sentinel
Recruitment Value Models
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class ScoreComponent:
    """
    Explainable score component.

    Every calculated score should be accompanied by
    a confidence estimate and a list of reasons.
    """

    score: float

    confidence: float = 100.0

    reasons: list[str] = field(
        default_factory=list,
    )


@dataclass(slots=True, frozen=True)
class RecruitmentValue:
    """
    Overall recruitment attractiveness of an alliance.
    """

    overall: ScoreComponent

    talent: ScoreComponent

    stability: ScoreComponent

    whale: ScoreComponent

    roster: ScoreComponent

    momentum: ScoreComponent