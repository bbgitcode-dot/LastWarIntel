"""
LastWarIntel
Intelligence Rule Engine
Version: 1.0

Generic rule engine used by intelligence modules.
"""

from __future__ import annotations

from analytics.intelligence.models import (
    IntelligenceReport,
    Rule,
    RuleContext,
    RuleResult,
)


class RuleEngine:
    """
    Evaluates a list of rules against one RuleContext.
    """

    def __init__(self, rules: list[Rule]):
        self.rules = sorted(rules, key=lambda rule: rule.priority)

    def evaluate(self, context: RuleContext, recommendation: str) -> IntelligenceReport:
        """
        Evaluate all rules and return an IntelligenceReport.
        """

        results: list[RuleResult] = []
        total_score = 0

        for rule in self.rules:
            result = rule.evaluator(context)
            results.append(result)

            if result.matched:
                total_score += result.points

        confidence = self._calculate_confidence(results)

        return IntelligenceReport(
            server=context.server,
            total_score=max(0, min(total_score, 100)),
            confidence=confidence,
            recommendation=recommendation,
            results=results,
        )

    @staticmethod
    def _calculate_confidence(results: list[RuleResult]) -> float:
        """
        Calculate confidence from matched evidence.

        v1 logic:
        More matched rules and more evidence increase confidence.
        """

        matched = [result for result in results if result.matched]

        if not matched:
            return 0.0

        matched_score = min(len(matched) * 15, 60)
        evidence_score = min(
            sum(len(result.evidence) for result in matched) * 8,
            40,
        )

        return round(matched_score + evidence_score, 2)