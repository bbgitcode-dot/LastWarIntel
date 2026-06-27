"""
Sentinel
Rule-Based Reasoning Engine
"""

from __future__ import annotations

from analytics.reasoning.models import (
    Assessment,
    FactSeverity,
    IntelligenceFact,
    ReasoningResult,
    Recommendation,
)


class RuleBasedReasoningEngine:
    """
    First-generation reasoning engine.

    This engine intentionally contains only
    deterministic rules.

    A future LLM implementation can replace
    this class without affecting callers.
    """

    def reason(
        self,
        facts: list[IntelligenceFact],
    ) -> ReasoningResult:

        if not facts:
            return ReasoningResult()

        highest = max(
            facts,
            key=lambda f: self._severity_value(
                f.severity,
            ),
        )

        assessment = Assessment(
            title=highest.title,
            summary=highest.description,
        )

        recommendation = Recommendation(
            title="Review Situation",
            description=(
                "Review the supporting evidence and "
                "consider strategic action."
            ),
            priority=highest.severity,
        )

        return ReasoningResult(
            facts=facts,
            assessment=assessment,
            recommendation=recommendation,
        )

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