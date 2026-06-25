"""
LastWarIntel
Intelligence Models
Version: 1.2

Shared models for rule-based intelligence, insights and executive briefings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from analytics.events.models import Severity


class InsightCategory(Enum):
    RISK = "Risk"
    OPPORTUNITY = "Opportunity"
    RECRUITMENT = "Recruitment"
    DIPLOMACY = "Diplomacy"
    GROWTH = "Growth"
    STABILITY = "Stability"
    COMPETITION = "Competition"
    GENERAL = "General"


class InsightPriority(Enum):
    CRITICAL = 100
    HIGH = 75
    MEDIUM = 50
    LOW = 25


@dataclass(slots=True)
class RuleContext:
    """
    Shared context passed into rules.
    """

    server: int
    events: list[Any] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RuleResult:
    """
    Result of one evaluated rule.
    """

    name: str
    matched: bool
    points: int
    explanation: str
    evidence: list[str] = field(default_factory=list)
    priority: int = 100


@dataclass(slots=True)
class Rule:
    """
    One explainable intelligence rule.
    """

    name: str
    description: str
    points: int
    priority: int
    evaluator: Callable[[RuleContext], RuleResult]


@dataclass(slots=True)
class IntelligenceReport:
    """
    Final result of a rule-based intelligence analysis.
    """

    server: int
    total_score: int
    confidence: float
    recommendation: str
    results: list[RuleResult] = field(default_factory=list)

    @property
    def matched_results(self) -> list[RuleResult]:
        return [result for result in self.results if result.matched]

    @property
    def evidence_count(self) -> int:
        return sum(len(result.evidence) for result in self.matched_results)


@dataclass(slots=True)
class Insight:
    """
    High-level interpretation generated from facts, events, scores,
    assessments or recruitment targets.
    """

    title: str
    summary: str
    confidence: float
    severity: Severity
    evidence: list[str] = field(default_factory=list)
    recommendation: str | None = None
    category: InsightCategory = InsightCategory.GENERAL
    priority: InsightPriority = InsightPriority.MEDIUM