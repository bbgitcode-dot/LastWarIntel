"""
Sentinel
Recruitment Advisor Facade
"""

from __future__ import annotations

from analytics.intelligence.indicators import StrategicIndicator
from analytics.reasoning.models import IntelligenceFact

from application.recruitment_advisor.builder import (
    RecruitmentAdvisorBuilder,
)


class RecruitmentAdvisorFacade:
    """
    Public entry point for recruitment advice.
    """

    def __init__(
        self,
    ) -> None:

        self._builder = RecruitmentAdvisorBuilder()

    def advise(
        self,
        server: int,
        alliance: str,
        facts: list[IntelligenceFact],
        indicators: list[StrategicIndicator],
    ):

        return self._builder.build(
            server=server,
            alliance=alliance,
            facts=facts,
            indicators=indicators,
        )