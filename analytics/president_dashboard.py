"""
LastWarIntel
President Dashboard
Version: 2.0

Executive strategic briefing for alliance leadership.
"""

from __future__ import annotations

import argparse

from analytics.events.analyzer import AllianceEventAnalyzer
from analytics.health.analyzer import AllianceHealthAnalyzer
from analytics.intelligence.insight_engine import InsightEngine
from analytics.recruitment.analyzer import RecruitmentTargetAnalyzer
from analytics.scoring.growth import GrowthScore
from analytics.scoring.overall import OverallScore
from analytics.scoring.stability import StabilityScore
from analytics.views.brief_builder import ExecutiveBriefBuilder
from analytics.views.formatter import ConsoleFormatter
from analytics.views.models import IntelligenceView
from analytics.views.president import PresidentViewBuilder


def build_dashboard(server: int) -> str:
    # ------------------------------------------------------------------
    # Scores
    # ------------------------------------------------------------------

    overall = OverallScore().calculate(server)["overall"]
    growth = GrowthScore().calculate(server)
    stability = StabilityScore().calculate(server)

    # ------------------------------------------------------------------
    # Intelligence
    # ------------------------------------------------------------------

    events = AllianceEventAnalyzer().analyze(server)
    health = AllianceHealthAnalyzer().analyze(server)
    recruitment = RecruitmentTargetAnalyzer().analyze_server(server)
    insights = InsightEngine().analyze(server)

    # ------------------------------------------------------------------
    # Executive Brief
    # ------------------------------------------------------------------

    brief = ExecutiveBriefBuilder().build(insights)

    # ------------------------------------------------------------------
    # President View
    # ------------------------------------------------------------------

    view = PresidentViewBuilder().build(
        server=server,
        overall_score=overall,
        growth=growth.raw_value,
        volatility=stability.raw_value,
        events=events,
        health_assessments=health,
        recruitment_targets=recruitment,
        insights=insights,
    )

    # ------------------------------------------------------------------
    # Insert Executive Brief directly after Executive Summary
    # ------------------------------------------------------------------

    order = 6

    preferred_order = [
        "Strategic Risks",
        "Strategic Opportunities",
        "Recruitment",
        "Growth",
        "Competition",
        "Stability",
        "Diplomacy",
        "General",
        "Recommended Actions",
    ]

    for section_name in preferred_order:
        items = brief.get(section_name, [])

        if not items:
            continue

        view.add_section(
            title=section_name,
            order=order,
            items=items,
        )

        order += 1

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    return ConsoleFormatter().render(view)


def parse_args():
    parser = argparse.ArgumentParser(
        description="President strategic dashboard."
    )

    parser.add_argument(
        "server",
        type=int,
        help="Server number",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print(build_dashboard(args.server))