"""
LastWarIntel
Topic Builder
Version: 1.0

Groups related insights into strategic intelligence topics.
"""

from __future__ import annotations

from collections import defaultdict

from analytics.events.models import Severity
from analytics.intelligence.models import (
    Insight,
    InsightCategory,
    InsightPriority,
    IntelligenceTopic,
)


class TopicBuilder:
    """
    Consolidates individual insights into higher-level strategic topics.
    """

    def build(self, insights: list[Insight]) -> list[IntelligenceTopic]:
        grouped: dict[InsightCategory, list[Insight]] = defaultdict(list)

        for insight in insights:
            grouped[insight.category].append(insight)

        topics: list[IntelligenceTopic] = []

        for category, category_insights in grouped.items():
            topics.append(self._build_topic(category, category_insights))

        return sorted(
            topics,
            key=lambda topic: (
                -topic.priority.value,
                -topic.confidence,
                topic.title,
            ),
        )

    def _build_topic(
        self,
        category: InsightCategory,
        insights: list[Insight],
    ) -> IntelligenceTopic:

        highest_priority = max(
            insights,
            key=lambda i: i.priority.value,
        )

        highest_severity = max(
            insights,
            key=lambda i: i.severity.value,
        )

        confidence = (
            sum(i.confidence for i in insights)
            / len(insights)
        )

        evidence: list[str] = []

        recommendations: list[str] = []

        for insight in insights:
            evidence.extend(insight.evidence)

            if (
                insight.recommendation
                and insight.recommendation not in recommendations
            ):
                recommendations.append(insight.recommendation)

        summary = self._build_summary(category, insights)

        return IntelligenceTopic(
            title=category.value,
            category=category,
            priority=highest_priority.priority,
            severity=highest_severity.severity,
            summary=summary,
            confidence=confidence,
            insights=sorted(
                insights,
                key=lambda i: (
                    -i.priority.value,
                    -i.confidence,
                ),
            ),
            evidence=evidence,
            recommendation=(
                recommendations[0]
                if recommendations
                else None
            ),
        )

    @staticmethod
    def _build_summary(
        category: InsightCategory,
        insights: list[Insight],
    ) -> str:

        count = len(insights)

        if category == InsightCategory.RISK:
            return f"{count} strategic risk(s) require attention."

        if category == InsightCategory.RECRUITMENT:
            return f"{count} recruitment opportunity identified."

        if category == InsightCategory.GROWTH:
            return f"{count} growth-related observation available."

        if category == InsightCategory.COMPETITION:
            return f"{count} competitive development detected."

        if category == InsightCategory.STABILITY:
            return f"{count} stability-related observation available."

        if category == InsightCategory.DIPLOMACY:
            return f"{count} diplomacy-related observation available."

        if category == InsightCategory.OPPORTUNITY:
            return f"{count} strategic opportunity identified."

        return f"{count} intelligence item(s)."