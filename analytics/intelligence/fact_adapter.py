"""
Sentinel
Intelligence Fact Adapter
"""

from __future__ import annotations

from analytics.intelligence.models import (
    Hypothesis,
    HypothesisCategory,
    IntelligencePriority,
)
from analytics.reasoning.models import (
    FactSeverity,
    IntelligenceFact,
)


class IntelligenceFactAdapter:
    """
    Converts IntelligenceFact objects into strategic hypotheses.

    This bridges the fact-based intelligence pipeline
    with the existing hypothesis / assessment pipeline.
    """

    def convert(
        self,
        facts: list[IntelligenceFact],
    ) -> list[Hypothesis]:
        sorted_facts = sorted(
            facts,
            key=lambda fact: (
                self._severity_value(fact.severity),
                fact.confidence,
            ),
            reverse=True,
        )

        return [
            self._convert_fact(fact)
            for fact in sorted_facts
        ]

    def _convert_fact(
        self,
        fact: IntelligenceFact,
    ) -> Hypothesis:
        return Hypothesis(
            title=fact.title,
            summary=fact.description,
            confidence=fact.confidence,
            priority=self._priority_from_severity(
                fact.severity,
            ),
            category=self._category_from_source(
                fact.source,
            ),
            evidence=fact.evidence,
        )

    @staticmethod
    def _priority_from_severity(
        severity: FactSeverity,
    ) -> IntelligencePriority:
        if severity == FactSeverity.CRITICAL:
            return IntelligencePriority.CRITICAL

        if severity == FactSeverity.HIGH:
            return IntelligencePriority.HIGH

        if severity == FactSeverity.MEDIUM:
            return IntelligencePriority.MEDIUM

        return IntelligencePriority.LOW

    @staticmethod
    def _severity_value(
        severity: FactSeverity,
    ) -> int:
        mapping = {
            FactSeverity.LOW: 1,
            FactSeverity.MEDIUM: 2,
            FactSeverity.HIGH: 3,
            FactSeverity.CRITICAL: 4,
        }

        return mapping[severity]

    @staticmethod
    def _category_from_source(
        source: str,
    ) -> HypothesisCategory:
        normalized = source.casefold()

        if "whale" in normalized:
            return HypothesisCategory.RECRUITMENT

        if "growth" in normalized:
            return HypothesisCategory.GROWTH

        if "leadership" in normalized:
            return HypothesisCategory.LEADERSHIP

        if "diplomacy" in normalized:
            return HypothesisCategory.DIPLOMACY

        if "collapse" in normalized:
            return HypothesisCategory.COLLAPSE

        if "alliance" in normalized:
            return HypothesisCategory.UNKNOWN

        return HypothesisCategory.UNKNOWN