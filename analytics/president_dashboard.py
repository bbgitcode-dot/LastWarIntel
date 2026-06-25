"""
LastWarIntel
President Dashboard
Version: 1.0

High-level strategic dashboard for alliance leadership.
"""

from __future__ import annotations

import argparse

from analytics.events.analyzer import AllianceEventAnalyzer
from analytics.health.analyzer import AllianceHealthAnalyzer
from analytics.recruitment.analyzer import RecruitmentTargetAnalyzer
from analytics.scoring.growth import GrowthScore
from analytics.scoring.overall import OverallScore
from analytics.scoring.stability import StabilityScore
from analytics.views.formatter import ConsoleFormatter
from analytics.views.president import PresidentViewBuilder


def build_dashboard(server: int):
    # ----- Scores -----

    overall = OverallScore().calculate(server)["overall"]
    growth = GrowthScore().calculate(server)
    stability = StabilityScore().calculate(server)

    # ----- Intelligence -----

    events = AllianceEventAnalyzer().analyze(server)
    health = AllianceHealthAnalyzer().analyze(server)
    recruitment = RecruitmentTargetAnalyzer().analyze_server(server)

    # ----- View -----

    view = PresidentViewBuilder().build(
        server=server,
        overall_score=overall,
        growth=growth.raw_value,
        volatility=stability.raw_value,
        events=events,
        health_assessments=health,
        recruitment_targets=recruitment,
    )

    return ConsoleFormatter().render(view)


def parse_args():
    parser = argparse.ArgumentParser(
        description="President strategic dashboard."
    )

    parser.add_argument("server", type=int)

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print(build_dashboard(args.server))