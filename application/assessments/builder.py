"""
Sentinel
Assessment Builder
"""

from __future__ import annotations

from analytics.reasoning.models import (
    FactSeverity,
    ReasoningResult,
)

from application.assessments.models import (
    Assessment,
    AssessmentSeverity,
)


class AssessmentBuilder:
    """
    Builds application-level assessments from reasoning results.
    """

    def build_from_reasoning(
        self,
        reasoning: ReasoningResult,
    ) -> Assessment | None:

        if reasoning.assessment is None:
            return None

        recommendation = ""

        if reasoning.recommendation is not None:
            recommendation = reasoning.recommendation.description

        evidence: list[str] = []

        for hypothesis in reasoning.hypotheses:
            evidence.extend(hypothesis.evidence)

        if not evidence:
            for fact in reasoning.facts:
                evidence.extend(fact.evidence or [fact.description])

        return Assessment(
            title=reasoning.assessment.title,
            summary=reasoning.assessment.summary,
            severity=self._severity(reasoning),
            confidence=self._confidence(reasoning),
            recommendation=recommendation,
            evidence=evidence,
            source="Reasoning",
        )

    @staticmethod
    def _severity(
        reasoning: ReasoningResult,
    ) -> AssessmentSeverity:

        if reasoning.recommendation is None:
            return AssessmentSeverity.LOW

        mapping = {
            FactSeverity.LOW: AssessmentSeverity.LOW,
            FactSeverity.MEDIUM: AssessmentSeverity.MEDIUM,
            FactSeverity.HIGH: AssessmentSeverity.HIGH,
            FactSeverity.CRITICAL: AssessmentSeverity.CRITICAL,
        }

        return mapping[reasoning.recommendation.priority]

    @staticmethod
    def _confidence(
        reasoning: ReasoningResult,
    ) -> float:

        if reasoning.hypotheses:
            return round(
                max(
                    hypothesis.confidence
                    for hypothesis in reasoning.hypotheses
                ),
                2,
            )

        if reasoning.facts:
            return round(
                sum(fact.confidence for fact in reasoning.facts)
                / len(reasoning.facts),
                2,
            )

        return 0.0