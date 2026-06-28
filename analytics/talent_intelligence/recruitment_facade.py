"""
Sentinel
Recruitment Value Facade
"""

from __future__ import annotations

from analytics.talent_intelligence.calculator import (
    RecruitmentValueCalculator,
)
from analytics.talent_intelligence.recruitment_context import (
    RecruitmentContext,
)
from analytics.talent_intelligence.recruitment_value import (
    RecruitmentValue,
)


class RecruitmentValueFacade:
    """
    Public entry point for recruitment value analysis.
    """

    def __init__(
        self,
    ) -> None:

        self._calculator = RecruitmentValueCalculator()

    def calculate(
        self,
        context: RecruitmentContext,
    ) -> RecruitmentValue:

        return self._calculator.calculate(
            context,
        )