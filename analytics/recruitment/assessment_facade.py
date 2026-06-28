"""Recruitment assessment facade.

The facade provides a small, explicit entry point for recruitment-specific
assessment evaluation while still delegating orchestration to the generic
Assessment Engine.
"""

from __future__ import annotations

from analytics.assessment_engine.engine import AssessmentEngine
from analytics.assessment_engine.models import AssessmentContext, AssessmentResult
from analytics.recruitment.assessment_rules import RecruitmentWindowRule


class RecruitmentAssessmentFacade:
    """Evaluate recruitment assessment rules."""

    def __init__(self) -> None:
        self._engine = AssessmentEngine([RecruitmentWindowRule()])

    def evaluate_context(self, context: AssessmentContext) -> AssessmentResult:
        """Evaluate recruitment assessments for one context."""
        return self._engine.evaluate(context)
