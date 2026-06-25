"""
LastWarIntel
Recommendation Engine
Version: 1.0

Generates strategic recommendations from strategic hypotheses.
"""

from __future__ import annotations

from analytics.intelligence.models import (
    Recommendation,
    StrategicAssessment,
)
from analytics.intelligence.rules.collapse_rule import CollapseRecommendationRule
from analytics.intelligence.rules.recommendation_rule import RecommendationRule


class RecommendationEngine:
    """
    Executes all recommendation rules.
    """

    def __init__(self) -> None:

        self._rules: list[RecommendationRule] = [
            CollapseRecommendationRule(),
        ]

    def generate(
        self,
        assessment: StrategicAssessment,
    ) -> StrategicAssessment:

        recommendations: list[Recommendation] = []

        for rule in self._rules:
            recommendations.extend(rule.evaluate(assessment))

        return StrategicAssessment(
            server=assessment.server,
            alliance=assessment.alliance,
            hypotheses=assessment.hypotheses,
            recommendations=recommendations,
        )