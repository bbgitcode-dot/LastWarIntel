"""
LastWarIntel
Topic Builder
Version: 1.1

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

        insights = sorted(
            insights,
            key=lambda i: (
                -i.priority.value,
                -i.confidence,
            ),
        )

        primary = insights[0]

        confidence = (
            sum(i.confidence for i in insights)
            / len(insights)
        )

        evidence: list[str] = []

        recommendations: list[str] = []

        for insight in insights:

            for item in insight.evidence:
                if item not in evidence:
                    evidence.append(item)

            if (
                insight.recommendation
                and insight.recommendation not in recommendations
            ):
                recommendations.append(insight.recommendation)

        summary = self._build_summary(insights)

        return IntelligenceTopic(
            title=category.value,
            category=category,
            priority=primary.priority,
            severity=primary.severity,
            summary=summary,
            confidence=confidence,
            insights=insights,
            evidence=evidence,
            recommendation=(
                recommendations[0]
                if recommendations
                else None
            ),
        )

    @staticmethod
    def _build_summary(insights: list[Insight]) -> str:
        """
        Create a natural-language topic summary.

        If only one insight exists, reuse its wording.
        Otherwise build a concise aggregation.
        """

        if len(insights) == 1:
            return insights[0].summary

        return (
            f"{len(insights)} related intelligence findings "
            f"support this topic."
        )