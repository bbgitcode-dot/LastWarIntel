"""
Sentinel
Talent Intelligence Facade
"""

from __future__ import annotations

from analytics.matching.models import MatchCandidate
from analytics.talent_intelligence.analyzer import (
    TalentIntelligenceAnalyzer,
)
from analytics.talent_intelligence.indicator_builder import (
    TalentIndicatorBuilder,
)
from analytics.talent_intelligence.models import TalentAssessment


class TalentIntelligenceFacade:
    """
    Public entry point for talent intelligence.
    """

    def __init__(self) -> None:
        self._analyzer = TalentIntelligenceAnalyzer()
        self._indicator_builder = TalentIndicatorBuilder()

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