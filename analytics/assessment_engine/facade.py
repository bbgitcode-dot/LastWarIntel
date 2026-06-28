"""Public facade for the Sentinel Assessment Engine."""

from __future__ import annotations

from analytics.assessment_engine.engine import AssessmentEngine
from analytics.assessment_engine.models import (
    AssessmentContext,
    AssessmentResult,
    AssessmentTarget,
)
from analytics.assessment_engine.base_rule import AssessmentRule
from analytics.assessment_engine.rules import default_assessment_rules
from analytics.intelligence.indicators import StrategicIndicator
from analytics.reasoning.models import IntelligenceFact, ReasoningHypothesis


class AssessmentEngineFacade:
    """High-level API for producing strategic assessments."""

    def __init__(self, rules: list[AssessmentRule] | None = None) -> None:
        self._engine = AssessmentEngine(rules or default_assessment_rules())

    def evaluate_context(self, context: AssessmentContext) -> AssessmentResult:
        return self._engine.evaluate(context)

    def evaluate(
        self,
        *,
        facts: list[IntelligenceFact] | None = None,
        indicators: list[StrategicIndicator] | None = None,
        hypotheses: list[ReasoningHypothesis] | None = None,
        target: AssessmentTarget | None = None,
    ) -> AssessmentResult:
        return self.evaluate_context(
            AssessmentContext.from_lists(
                facts=facts,
                indicators=indicators,
                hypotheses=hypotheses,
                target=target,
            )
        )
