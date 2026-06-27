"""
Sentinel
Reasoning Models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FactSeverity(Enum):
    """
    Importance of an intelligence fact.
    """

    LOW = "Low"

    MEDIUM = "Medium"

    HIGH = "High"

    CRITICAL = "Critical"


@dataclass(slots=True, frozen=True)
class IntelligenceFact:
    """
    One atomic intelligence fact produced by an intelligence module.

    Examples:

    - 3 whales transferred
    - Alliance lost 18% power
    - Recruitability increased
    """

    source: str

    title: str

    description: str

    severity: FactSeverity

    confidence: float = 100.0

    evidence: list[str] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class Assessment:
    """
    Human-readable assessment generated
    from one or more intelligence facts.
    """

    title: str

    summary: str


@dataclass(slots=True, frozen=True)
class Recommendation:
    """
    Suggested action.
    """

    title: str

    description: str

    priority: FactSeverity


@dataclass(slots=True, frozen=True)
class ReasoningResult:
    """
    Final reasoning output.

    Every reasoning result consists of

    Facts

    ↓

    Assessment

    ↓

    Recommendation
    """

    facts: list[IntelligenceFact] = field(default_factory=list)

    assessment: Assessment | None = None

    recommendation: Recommendation | None = None