"""
LastWarIntel
President View Builder
Version: 1.0

Builds a President Intelligence View from already available assessments.
"""

from __future__ import annotations

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
    ) -> IntelligenceView:

        view = IntelligenceView(
            title=f"SERVER {server} PRESIDENT INTELLIGENCE",
            subtitle="Strategic overview",
        )

        # ----------------------------------------------------------
        # Overview
        # ----------------------------------------------------------

        view.add_section(
            "Overview",
            10,
            [
                f"Overall Score : {overall_score:.2f}",
                f"Growth        : {growth:+.2f}%",
                f"Volatility    : {volatility:.2f}%",
                f"Events        : {len(events)}",
                f"Alliances     : {len(health_assessments)}",
            ],
        )

        # ----------------------------------------------------------
        # Critical Alliances
        # ----------------------------------------------------------

        critical = sorted(
            health_assessments,
            key=lambda h: h.score,
        )[:5]

        items = []

        for alliance in critical:
            items.append(
                f"{alliance.alliance:<8} "
                f"{alliance.score:>3}/100 "
                f"{alliance.status:<10} "
                f"{alliance.trend}"
            )

        view.add_section(
            "Critical / Weak Alliances",
            20,
            items,
        )

        # ----------------------------------------------------------
        # Strong Alliances
        # ----------------------------------------------------------

        strongest = sorted(
            health_assessments,
            key=lambda h: h.score,
            reverse=True,
        )[:5]

        items = []

        for alliance in strongest:
            items.append(
                f"{alliance.alliance:<8} "
                f"{alliance.score:>3}/100 "
                f"{alliance.status:<10} "
                f"{alliance.trend}"
            )

        view.add_section(
            "Strong Alliances",
            30,
            items,
        )

        # ----------------------------------------------------------
        # Recruitment
        # ----------------------------------------------------------

        items = []

        for target in recruitment_targets[:5]:
            items.append(
                f"{target.alliance:<8} "
                f"{target.priority:>3}/100 "
                f"{target.recommendation}"
            )

        view.add_section(
            "Recruitment Opportunities",
            40,
            items,
        )

        # ----------------------------------------------------------
        # Recent Events
        # ----------------------------------------------------------

        items = []

        for event in events[:10]:
            items.append(
                f"[{event.severity.name}] "
                f"{event.summary}"
            )

        view.add_section(
            "Recent Events",
            50,
            items,
        )

        return view