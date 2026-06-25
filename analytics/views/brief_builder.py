"""
LastWarIntel
Executive Brief Builder
Version: 1.0

Transforms insights into executive briefing sections.
"""

from __future__ import annotations

from analytics.intelligence.models import (
    Insight,
    InsightCategory,
)


class ExecutiveBriefBuilder:
    """
    Groups insights into an executive briefing.

    The output is intentionally presentation-agnostic and can later be
    rendered by console, HTML, Discord or PDF formatters.
    """

    def build(self, insights: list[Insight]) -> dict[str, list[str]]:
        sections = {
            "Strategic Risks": [],
            "Strategic Opportunities": [],
            "Recruitment": [],
            "Growth": [],
            "Competition": [],
            "Stability": [],
            "Diplomacy": [],
            "General": [],
            "Recommended Actions": [],
        }

        severity_icons = {
            "CRITICAL": "⛔",
            "HIGH": "🔴",
            "MEDIUM": "🟠",
            "LOW": "🟢",
        }

        for insight in sorted(
            insights,
            key=lambda i: (
                -i.priority.value,
                -i.confidence,
                i.title,
            ),
        ):
            icon = severity_icons.get(insight.severity.name, "•")

            line = (
                f"{icon} {insight.summary} "
                f"(Confidence {insight.confidence:.0f}%)"
            )

            if insight.category == InsightCategory.RISK:
                sections["Strategic Risks"].append(line)

            elif insight.category == InsightCategory.OPPORTUNITY:
                sections["Strategic Opportunities"].append(line)

            elif insight.category == InsightCategory.RECRUITMENT:
                sections["Recruitment"].append(line)

            elif insight.category == InsightCategory.GROWTH:
                sections["Growth"].append(line)

            elif insight.category == InsightCategory.COMPETITION:
                sections["Competition"].append(line)

            elif insight.category == InsightCategory.STABILITY:
                sections["Stability"].append(line)

            elif insight.category == InsightCategory.DIPLOMACY:
                sections["Diplomacy"].append(line)

            else:
                sections["General"].append(line)

            if insight.recommendation:
                sections["Recommended Actions"].append(
                    f"• {insight.recommendation}"
                )

        return sections