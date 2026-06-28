"""
Sentinel
Talent Intelligence Facade
"""

from __future__ import annotations

from analytics.intelligence.indicators import StrategicIndicator
from analytics.matching.models import MatchCandidate
from analytics.talent_intelligence.analyzer import (
    TalentIntelligenceAnalyzer,
)
from analytics.talent_intelligence.indicator_builder import (
    TalentIndicatorBuilder,
)
from analytics.talent_intelligence.models import TalentAssessment
from analytics.talent_intelligence.recruitment_context_builder import (
    RecruitmentContextBuilder,
)
from analytics.talent_intelligence.recruitment_value import (
    RecruitmentValue,
)
from analytics.talent_intelligence.recruitment_facade import (
    RecruitmentValueFacade,
)


class TalentIntelligenceFacade:
    """
    Public entry point for talent intelligence.
    """

    def __init__(self) -> None:
        self._analyzer = TalentIntelligenceAnalyzer()
        self._indicator_builder = TalentIndicatorBuilder()
        self._recruitment_context_builder = RecruitmentContextBuilder()
        self._recruitment_value = RecruitmentValueFacade()

    def analyze(
        self,
        players: list[MatchCandidate],
    ) -> TalentAssessment:

        assessment = self._analyzer.analyze(players)

        indicators = self._indicator_builder.build(assessment)

        return TalentAssessment(
            metrics=assessment.metrics,
            indicators=indicators,
        )

    def recruitment_value(
        self,
        indicators: list[StrategicIndicator],
    ) -> RecruitmentValue:

        context = self._recruitment_context_builder.build(
            indicators,
        )

        return self._recruitment_value.calculate(
            context,
        )