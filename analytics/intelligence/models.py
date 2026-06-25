"""
LastWarIntel
Intelligence Rule Engine
Version: 1.0

Shared models for rule-based intelligence modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Any


@dataclass(slots=True)
class RuleContext:
    """
    Shared context passed into rules.

    The context contains all information a rule may need.
    It keeps rules independent from SQL and CLI output.
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