"""
LastWarIntel
Module: Recruitment Intelligence CLI
Version: 3.0

Recruitment v3 uses:
- Alliance Events
- Scoring Results
- Rule Engine

It does not directly calculate recruitment logic inside the CLI.
"""

from __future__ import annotations

from analytics.events.analyzer import AllianceEventAnalyzer
from analytics.intelligence.engine import RuleEngine
from analytics.intelligence.models import RuleContext
from analytics.intelligence.recruitment_rules import build_recruitment_rules
from analytics.scoring.growth import GrowthScore
from analytics.scoring.overall import OverallScore
from analytics.scoring.player import PlayerScore
from analytics.scoring.stability import StabilityScore
from services.server_repository import ServerRepository


def format_percent(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


def classify_score(score: int) -> str:
    if score >= 80:
        return "★★★★★ Hot Target"
    if score >= 60:
        return "★★★★☆ Strong Opportunity"
    if score >= 40:
        return "★★★☆☆ Potential Target"
    if score >= 20:
        return "★★☆☆☆ Observation"
    return "★☆☆☆☆ Low Priority"


def build_context(server: int) -> RuleContext:
    events = AllianceEventAnalyzer().analyze(server)

    growth = GrowthScore().calculate(server)
    stability = StabilityScore().calculate(server)
    player = PlayerScore().calculate(server)
    overall = OverallScore().calculate(server)

    return RuleContext(
        server=server,
        events=events,
        scores={
            "growth": growth.score,
            "growth_raw": growth.raw_value or 0,
            "stability": stability.score,
            "stability_raw": stability.raw_value or 0,
            "player": player.score,
            "player_raw": player.raw_value or 0,
            "overall": overall["overall"],
        },
    )


def analyze_server(server: int):
    context = build_context(server)

    engine = RuleEngine(build_recruitment_rules())

    report = engine.evaluate(
        context=context,
        recommendation="Recruitment Opportunity",
    )

    report.recommendation = classify_score(report.total_score)

    return report, context


def active_servers():
    repo = ServerRepository()

    servers = []

    for row in repo.get_all_servers():
        server = row["server"]

        if repo.has_complete_scoring_data(server):
            servers.append(server)

    return servers


def print_report():
    reports = []

    for server in active_servers():
        report, context = analyze_server(server)
        reports.append((report, context))

    reports.sort(key=lambda item: item[0].total_score, reverse=True)

    print()
    print("========== RECRUITMENT INTELLIGENCE v3 ==========")
    print()
    print(
        f"{'#':>2}  "
        f"{'Server':<8} "
        f"{'Score':>5} "
        f"{'Conf.':>7} "
        f"{'Growth':>9} "
        f"{'Volatility':>11} "
        f"{'Overall':>8}  "
        f"Recommendation"
    )
    print("-" * 100)

    for idx, (report, context) in enumerate(reports, start=1):
        growth = context.scores.get("growth_raw", 0)
        volatility = context.scores.get("stability_raw", 0)
        overall = context.scores.get("overall", 0)

        print(
            f"{idx:>2}. "
            f"{report.server:<8} "
            f"{report.total_score:>5} "
            f"{report.confidence:>6.1f}% "
            f"{format_percent(growth):>9} "
            f"{volatility:>10.2f}% "
            f"{overall:>8.2f}  "
            f"{report.recommendation}"
        )

        matched = report.matched_results

        if matched:
            print("     Matched rules:")

            for result in matched:
                sign = "+" if result.points >= 0 else ""
                print(
                    f"       {sign}{result.points:>3} "
                    f"{result.name}: {result.explanation}"
                )

                for evidence in result.evidence[:3]:
                    print(f"           - {evidence}")

                if len(result.evidence) > 3:
                    print(f"           - ... {len(result.evidence) - 3} more")

        else:
            print("     No recruitment rules matched.")

        print()


if __name__ == "__main__":
    print_report()