"""
LastWarIntel
President View Builder
Version: 3.0

Builds the President Intelligence View.

Rendering of intelligence topics is delegated to TopicRenderer.
"""

from __future__ import annotations

from analytics.intelligence.models import IntelligenceTopic
from analytics.views.models import IntelligenceView
from analytics.views.topic_renderer import TopicRenderer


class PresidentViewBuilder:
    """
    Creates the executive intelligence dashboard.
    """

    def __init__(self) -> None:
        self._topics = TopicRenderer()

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
        topics: list[IntelligenceTopic],
    ) -> IntelligenceView:

        view = IntelligenceView(
            title=f"SERVER {server} PRESIDENT INTELLIGENCE",
            subtitle="Strategic overview",
        )

        # ------------------------------------------------------------
        # Executive Summary
        # ------------------------------------------------------------

        view.add_section(
            "Executive Summary",
            5,
            self._topics.render_executive_summary(topics),
        )

        # ------------------------------------------------------------
        # Strategic Topics
        # ------------------------------------------------------------

        view.add_section(
            "Strategic Topics",
            10,
            self._topics.render_topics(topics),
        )

        # ------------------------------------------------------------
        # Recommended Actions
        # ------------------------------------------------------------

        view.add_section(
            "Recommended Actions",
            15,
            self._topics.render_actions(topics),
        )

        # ------------------------------------------------------------
        # Current Situation
        # ------------------------------------------------------------

        view.add_section(
            "Current Situation",
            20,
            [
                f"Overall Score : {overall_score:.2f}/100",
                f"Growth        : {growth:+.2f}%",
                f"Volatility    : {volatility:.2f}%",
                f"Events        : {len(events)} detected",
                f"Alliances     : {len(health_assessments)} tracked",
                self._situation_summary(
                    overall_score,
                    growth,
                    volatility,
                ),
            ],
        )

        # ------------------------------------------------------------
        # Alliance Health
        # ------------------------------------------------------------

        weak = [
            alliance
            for alliance in health_assessments
            if alliance.score < 70
        ]

        if weak:
            view.add_section(
                "Critical / Weak Alliances",
                30,
                [
                    self._format_health(item)
                    for item in sorted(
                        weak,
                        key=lambda item: item.score,
                    )
                ],
            )

        watch = [
            alliance
            for alliance in health_assessments
            if 70 <= alliance.score < 80
        ]

        if watch:
            view.add_section(
                "Alliances to Watch",
                40,
                [
                    self._format_health(item)
                    for item in sorted(
                        watch,
                        key=lambda item: (item.risk, item.score),
                    )
                ],
            )

        strong = [
            alliance
            for alliance in health_assessments
            if alliance.score >= 80
        ]

        if strong:
            view.add_section(
                "Strong Alliances",
                50,
                [
                    self._format_health(item)
                    for item in sorted(
                        strong,
                        key=lambda item: item.score,
                        reverse=True,
                    )
                ],
            )

        # ------------------------------------------------------------
        # Recruitment
        # ------------------------------------------------------------

        if recruitment_targets:

            view.add_section(
                "Recruitment Opportunities",
                60,
                [
                    (
                        f"{target.alliance:<8}"
                        f"{target.priority:>4}/100 "
                        f"{target.recommendation:<20}"
                        f"Health {target.health:>3}/100 "
                        f"Risk {target.risk}"
                    )
                    for target in sorted(
                        recruitment_targets,
                        key=lambda target: target.priority,
                        reverse=True,
                    )[:10]
                ],
            )

        # ------------------------------------------------------------
        # Events
        # ------------------------------------------------------------

        high = [
            event
            for event in events
            if event.severity.name in ("CRITICAL", "HIGH")
        ]

        if high:
            view.add_section(
                "High Impact Events",
                70,
                [
                    f"[{event.severity.name}] {event.summary}"
                    for event in high[:10]
                ],
            )

        medium = [
            event
            for event in events
            if event.severity.name == "MEDIUM"
        ]

        if medium:
            view.add_section(
                "Medium Impact Events",
                80,
                [
                    f"[{event.severity.name}] {event.summary}"
                    for event in medium[:10]
                ],
            )

        return view

    @staticmethod
    def _format_health(item) -> str:
        return (
            f"{item.alliance:<8}"
            f"{item.score:>4}/100 "
            f"{item.status:<10}"
            f"{item.trend:<10}"
            f"Risk {item.risk}"
        )

    @staticmethod
    def _situation_summary(
        overall_score: float,
        growth: float,
        volatility: float,
    ) -> str:

        if overall_score >= 70 and growth > 10 and volatility < 8:
            return "Assessment    : Strong, growing and relatively stable server."

        if overall_score >= 55 and volatility >= 8:
            return "Assessment    : Competitive server with meaningful internal movement."

        if growth < 0 and volatility >= 10:
            return "Assessment    : Declining and volatile server. Watch for recruitment openings."

        if overall_score < 40:
            return "Assessment    : Low overall strength. Validate player value before investing effort."

        return "Assessment    : Mixed situation. Review events and alliance health."