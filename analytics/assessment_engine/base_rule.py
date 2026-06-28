"""Base rule protocol for Sentinel assessment rules.

Assessment rules are deterministic domain evaluators. They inspect one
AssessmentContext and may produce one StrategicAssessment. The Assessment Engine
owns orchestration only; domain knowledge belongs inside concrete rules.
"""

from __future__ import annotations

from typing import Protocol

from analytics.assessment_engine.models import AssessmentContext, StrategicAssessment


class AssessmentRule(Protocol):
    """Protocol implemented by all assessment rules.

    Rules must be deterministic. The same context must always produce the same
    assessment or no assessment. Rules must not persist data, mutate context,
    perform presentation work, or call other rules directly.
    """

    name: str
    priority: int

    def evaluate(self, context: AssessmentContext) -> StrategicAssessment | None:
        """Evaluate the context and optionally produce one assessment."""
