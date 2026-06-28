"""Generic Assessment Engine.

The engine orchestrates deterministic rules. It does not contain strategic
business logic itself; domain-specific assessment logic lives in rules.
"""

from __future__ import annotations

from analytics.assessment_engine.models import (
    AssessmentContext,
    AssessmentResult,
    StrategicAssessment,
)
from analytics.assessment_engine.base_rule import AssessmentRule


class AssessmentEngine:
    """Evaluate assessment rules against one context."""

    def __init__(self, rules: list[AssessmentRule]) -> None:
        self._rules = sorted(rules, key=lambda rule: rule.priority)

    def evaluate(self, context: AssessmentContext) -> AssessmentResult:
        assessments: list[StrategicAssessment] = []
        seen: set[tuple[str, str, str]] = set()

        for rule in self._rules:
            assessment = rule.evaluate(context)
            if assessment is None:
                continue

            key = (
                assessment.assessment_type.value,
                assessment.target.entity_type.value,
                assessment.target.entity_id,
            )
            if key in seen:
                continue

            seen.add(key)
            assessments.append(assessment)

        return AssessmentResult(assessments=tuple(assessments))
