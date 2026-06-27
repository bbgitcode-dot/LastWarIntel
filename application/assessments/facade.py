"""
Sentinel
Assessment Facade
"""

from __future__ import annotations

from analytics.reasoning.models import ReasoningResult

from application.assessments.builder import AssessmentBuilder


class AssessmentFacade:
    """
    Public entry point for application assessments.
    """

    def __init__(self) -> None:
        self._builder = AssessmentBuilder()

    def from_reasoning(
        self,
        reasoning: ReasoningResult,
    ):

        return self._builder.build_from_reasoning(reasoning)