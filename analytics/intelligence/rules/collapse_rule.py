"""
LastWarIntel
Collapse Recommendation Rule
Version: 1.0

Generates recommendations for collapsing alliances.
"""

from __future__ import annotations

from analytics.intelligence.models import (
    HypothesisCategory,
    IntelligencePriority,
    Recommendation,
    StrategicAssessment,
)
from analytics.intelligence.rules.recommendation_rule import RecommendationRule


class CollapseRecommendationRule(RecommendationRule):
    """
    Generates recommendations for collapsing alliances.
    """

    def evaluate(
        self,
        assessment: StrategicAssessment,
    ) -> list[Recommendation]:

        recommendations: list[Recommendation] = []

        for hypothesis in assessment.hypotheses:

            if hypothesis.category != HypothesisCategory.COLLAPSE:
                continue

            recommendations.append(
                Recommendation(
                    title="Contact remaining officers immediately",
                    description=(
                        "Reach out before competing servers recruit the remaining "
                        "leadership and high-value players."
                    ),
                    priority=IntelligencePriority.CRITICAL,
                    confidence=hypothesis.confidence,
                    rationale=list(hypothesis.evidence),
                )
            )

        return recommendations