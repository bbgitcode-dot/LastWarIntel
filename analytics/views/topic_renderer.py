"""
LastWarIntel
Topic Renderer
Version: 1.0

Responsible only for rendering IntelligenceTopic objects into
presentation-ready text.

No business logic belongs here.
"""

from __future__ import annotations

from analytics.intelligence.models import IntelligenceTopic


class TopicRenderer:
    """
    Renders IntelligenceTopic objects for console-style views.
    """

    _ICONS = {
        "CRITICAL": "⛔",
        "HIGH": "🔴",
        "MEDIUM": "🟠",
        "LOW": "🟢",
    }

    def render_executive_summary(
        self,
        topics: list[IntelligenceTopic],
        limit: int = 4,
    ) -> list[str]:
        """
        Render a compact executive summary.
        """

        if not topics:
            return ["No major strategic topics detected."]

        lines = []

        for topic in topics[:limit]:
            icon = self._icon(topic)

            lines.append(
                f"{icon} {topic.summary} "
                f"(Confidence {topic.confidence:.0f}%)"
            )

        return lines

    def render_topics(
        self,
        topics: list[IntelligenceTopic],
    ) -> list[str]:
        """
        Render all strategic topics.
        """

        if not topics:
            return ["No strategic topics available."]

        lines = []

        for topic in topics:

            icon = self._icon(topic)

            lines.append(
                f"{icon} "
                f"{topic.title:<12} "
                f"{topic.priority.name:<8} "
                f"{topic.summary} "
                f"(Confidence {topic.confidence:.0f}%)"
            )

            #
            # If multiple insights contributed to the topic,
            # show supporting insights.
            #
            if topic.insight_count > 1:

                for insight in topic.insights:
                    lines.append(
                        f"   • {insight.summary}"
                    )

        return lines

    def render_actions(
        self,
        topics: list[IntelligenceTopic],
    ) -> list[str]:
        """
        Render recommended actions.
        """

        actions: list[str] = []

        for topic in topics:

            recommendation = topic.recommendation

            if (
                recommendation
                and recommendation not in actions
            ):
                actions.append(recommendation)

        if not actions:
            return ["No direct actions recommended."]

        return [f"• {action}" for action in actions]

    @classmethod
    def _icon(cls, topic: IntelligenceTopic) -> str:
        return cls._ICONS.get(
            topic.severity.name,
            "•",
        )