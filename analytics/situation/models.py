"""
LastWarIntel
Situation Models
Version: 1.0

Domain models describing the current strategic situation of an alliance.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class SituationFinding:
    """
    A single relevant finding contributing to the overall situation.
    """

    title: str
    description: str
    confidence: float


@dataclass(slots=True, frozen=True)
class CurrentSituation:
    """
    Current strategic situation of an alliance.
    """

    summary: str

    findings: list[SituationFinding] = field(default_factory=list)

    confidence: float = 0.0