"""
LastWarIntel
President View Builder
Version: 1.2

Builds a strategic intelligence view for alliance leadership.
"""

from __future__ import annotations

from analytics.intelligence.models import Insight
from analytics.views.models import IntelligenceView


class PresidentViewBuilder:
    """
    Creates a high-level intelligence view for alliance leadership.
    """

    def build(
        self,
        *,
        server: int,
        overall_score: float,
        growth: float,
        volatility: float,
        events: list,
        health_assessments: list,
        recruitment_targets: list,
        insights: list[Insight],
    ) -> IntelligenceView:
        view = IntelligenceView(
            title=f"SERVER {server} PRESIDENT INTELLIGENCE",
            subtitle="Strategic overview",
        )

        view.add_section(
            "Executive Summary",
            5,
            self._format_insights(insights),
        )

        view.add_section(
            "Current Situation",
            10,
            [
                f"Overall Score : {overall_score:.2f}/100",
                f"Growth        : {growth:+.2f}%",
                f"Volatility    : {volatility:.2f}%",
                f"Events        : {len(events)} detected",
                f"Alliances     : {len(health_assessments)} tracked",
                self._situation_summary(overall_score, growth, volatility),
            ],
        )

        weak = [item for item in health_assessments if item.score < 70]
        view.add_section(
            "Critical / Weak Alliances",
            20,
            [self._format_health(item) for item in sorted(weak, key=lambda h: h.score)],
        )

        watch = [item for item in health_assessments if 70 <= item.score < 80]
        view.add_section(
            "Alliances to Watch",
            30,
            [
                self._format_health(item)
                for item in sorted(watch, key=lambda h: (h.risk, h.score))
            ],
        )

        strong = [item for item in health_assessments if item.score >= 80]
        view.add_section(
            "Strong Alliances",
            40,
            [
                self._format_health(item)
                for item in sorted(strong, key=lambda h: h.score, reverse=True)
            ],
        )

        actionable_targets = sorted(
            recruitment_targets,
            key=lambda item: item.priority,
            reverse=True,
        )[:10]

        view.add_section(
            "Recruitment Opportunities",
            50,
            [
                (
                    f"{target.alliance:<8} "
                    f"{target.priority:>3}/100 "
                    f"{target.recommendation:<20} "
                    f"Health {target.health:>3}/100 "
                    f"Risk {target.risk}"
                )
                for target in actionable_targets
            ],
        )

        high_events = [
            event for event in events
            if event.severity.name in ("CRITICAL", "HIGH")
        ]

        view.add_section(
            "High Impact Events",
            60,
            [
                f"[{event.severity.name}] {event.summary}"
                for event in high_events[:10]
            ],
        )

        medium_events = [
            event for event in events
            if event.severity.name == "MEDIUM"
        ]

        view.add_section(
            "Medium Impact Events",
            70,
            [
                f"[{event.severity.name}] {event.summary}"
                for event in medium_events[:10]
            ],
        )

        return view

    @staticmethod
    def _format_insights(insights: list[Insight]) -> list[str]:
        if not insights:
            return ["No major strategic insights detected."]

        severity_icons = {
            "CRITICAL": "⛔",
            "HIGH": "🔴",
            "MEDIUM": "🟠",
            "LOW": "🟢",
        }

        items = []

        for insight in insights:
            icon = severity_icons.get(insight.severity.name, "•")
            items.append(
                f"{icon} {insight.summary} "
                f"(Confidence {insight.confidence:.0f}%)"
            )

        return items

    @staticmethod
    def _format_health(item) -> str:
        return (
            f"{item.alliance:<8} "
            f"{item.score:>3}/100 "
            f"{item.status:<10} "
            f"{item.trend:<10} "
            f"Risk {item.risk}"
        )

    @staticmethod
    def _situation_summary(overall_score: float, growth: float, volatility: float) -> str:
        if overall_score >= 70 and growth > 10 and volatility < 8:
            return "Assessment    : Strong, growing and relatively stable server."

        if overall_score >= 55 and volatility >= 8:
            return "Assessment    : Competitive server with meaningful internal movement."

        if growth < 0 and volatility >= 10:
            return "Assessment    : Declining and volatile server. Watch for recruitment openings."

        if overall_score < 40:
            return "Assessment    : Low overall strength. Validate player value before investing effort."

        return "Assessment    : Mixed situation. Review events and alliance health."