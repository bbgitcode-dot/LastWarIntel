"""
LastWarIntel
Module: Entity Intelligence CLI
Version: 1.2

Creates a full intelligence file for one alliance on one server.

Shows:
- Facts / Timeline
- Timeline Metrics
- Timeline Trend
- Events
- Health Assessment
- Evidence
- Recruitment View
"""

import argparse

from analytics.assessment.converter import AllianceHealthAssessmentConverter
from analytics.events.analyzer import AllianceEventAnalyzer
from analytics.health.analyzer import AllianceHealthAnalyzer
from analytics.recruitment.analyzer import RecruitmentTargetAnalyzer
from analytics.timeline.facade import TimelineFacade
from services.server_repository import ServerRepository


def format_power(value):
    if value is None:
        return "-"

    sign = "-" if value < 0 else ""
    value = abs(value)

    if value >= 1_000_000_000:
        return f"{sign}{value / 1_000_000_000:.2f}B"

    if value >= 1_000_000:
        return f"{sign}{value / 1_000_000:.2f}M"

    return f"{sign}{value:,}".replace(",", ".")


def print_section(title):
    print()
    print(title)
    print("-" * 70)


def find_item(items, attr, value):
    for item in items:
        if getattr(item, attr) == value:
            return item

    return None


def print_entity_intelligence(server: int, alliance: str):
    repo = ServerRepository()

    histories = repo.get_all_alliance_histories(server)

    if alliance not in histories:
        print(f"Keine Daten für Allianz {alliance} auf Server {server}.")
        return

    history = histories[alliance]

    events = [
        event
        for event in AllianceEventAnalyzer().analyze(server)
        if event.entity == alliance
    ]

    health_items = AllianceHealthAnalyzer().analyze(server)
    health = find_item(health_items, "alliance", alliance)

    assessment = None
    if health:
        assessment = AllianceHealthAssessmentConverter().convert(health)

    timeline_result = TimelineFacade().analyze(server, alliance)

    timeline_metrics = None
    timeline_assessment = None

    if timeline_result:
        timeline_metrics = timeline_result.metrics
        timeline_assessment = timeline_result.assessment

    recruitment_targets = RecruitmentTargetAnalyzer().analyze_server(server)
    recruitment = find_item(recruitment_targets, "alliance", alliance)

    print()
    print("=" * 70)
    print("ALLIANCE INTELLIGENCE FILE")
    print("=" * 70)
    print()
    print(f"Server:   {server}")
    print(f"Alliance: {alliance}")

    print_section("FACTS / TIMELINE")

    for row in history:
        print(
            f"{row['collection']:<28} "
            f"Rank #{row['rank']:<2} "
            f"{format_power(row['power']):>10}"
        )

    print_section("TIMELINE METRICS")

    if timeline_metrics is None:
        print("No timeline metrics available.")
    else:
        print(f"Snapshots:       {timeline_metrics.snapshot_count}")
        print(
            f"Power:           "
            f"{format_power(timeline_metrics.first_power)} → "
            f"{format_power(timeline_metrics.last_power)}"
        )
        print(
            f"Rank:            "
            f"#{timeline_metrics.first_rank} → "
            f"#{timeline_metrics.last_rank}"
        )
        print(f"Total Growth:    {timeline_metrics.total_growth_percent:+.2f}%")
        print(f"Max Growth:      {timeline_metrics.max_growth_percent:+.2f}%")
        print(f"Max Drop:        {timeline_metrics.max_drop_percent:+.2f}%")
        print(f"Rank Gain:       {timeline_metrics.largest_rank_gain}")
        print(f"Rank Loss:       {timeline_metrics.largest_rank_loss}")
        print(f"Volatility:      {timeline_metrics.power_volatility:.2f}%")
        print(f"Missing Latest:  {timeline_metrics.missing_latest_snapshot}")

    print_section("TIMELINE TREND")

    if timeline_assessment is None:
        print("No timeline trend available.")
    else:
        print(f"Trend:      {timeline_assessment.trend.value}")
        print(f"Confidence: {timeline_assessment.confidence:.0f}%")
        print(f"Summary:    {timeline_assessment.summary}")

        if timeline_assessment.evidence:
            print()
            print("Evidence:")
            for item in timeline_assessment.evidence:
                print(f"  - {item}")

    print_section("EVENTS")

    if not events:
        print("No events detected.")
    else:
        for event in events:
            print(f"[{event.severity.name:<8}] {event.event_type.value}")
            print(f"  {event.summary}")

            if event.evidence:
                print(f"  Evidence: {' → '.join(event.evidence)}")

            if event.facts:
                print("  Facts:")
                for key, value in event.facts.items():
                    if "power" in key or key == "diff":
                        value = format_power(value)
                    elif isinstance(value, float):
                        value = f"{value:.2f}"

                    print(f"    {key}: {value}")

            print()

    print_section("ALLIANCE HEALTH")

    if not health:
        print("No health assessment available.")
    else:
        print(f"Score:  {health.score}/100")
        print(f"Status: {health.status}")
        print(f"Trend:  {health.trend}")
        print(f"Risk:   {health.risk}")

        print()
        print("Reasons:")
        for reason in health.reasons:
            print(f"  - {reason}")

    print_section("ASSESSMENT / EVIDENCE")

    if not assessment:
        print("No universal assessment available.")
    else:
        print(f"Assessment: {assessment.assessment_type.value}")
        print(f"Score:      {assessment.score}/100")
        print(f"Confidence: {assessment.confidence}%")
        print(f"Summary:    {assessment.summary}")

        print()
        print("Evidence:")
        for item in assessment.evidence:
            print(f"  - [{item.source}] {item.title}")
            print(f"    {item.explanation}")
            print(f"    Weight: {item.weight} | Confidence: {item.confidence}%")

    print_section("RECRUITMENT VIEW")

    if not recruitment:
        print("No recruitment target generated.")
    else:
        print(f"Priority:       {recruitment.priority}/100")
        print(f"Confidence:     {recruitment.confidence}%")
        print(f"Recommendation: {recruitment.recommendation}")
        print(f"Health:         {recruitment.health}/100")
        print(f"Risk:           {recruitment.risk}")

        print()
        print("Recruitment Reasons:")
        for reason in recruitment.reasons:
            print(f"  - {reason}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Show complete intelligence file for one alliance."
    )

    parser.add_argument("server", type=int)
    parser.add_argument("alliance", type=str)

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print_entity_intelligence(args.server, args.alliance)