"""
LastWarIntel
Module: Entity Intelligence CLI
Version: 1.0

Creates a full intelligence file for one alliance on one server.

Shows:
- Facts
- Timeline
- Events
- Health Assessment
- Evidence
- Recruitment Target
"""

import argparse

from analytics.assessment.converter import AllianceHealthAssessmentConverter
from analytics.events.analyzer import AllianceEventAnalyzer
from analytics.health.analyzer import AllianceHealthAnalyzer
from analytics.recruitment.analyzer import RecruitmentTargetAnalyzer
from services.server_repository import ServerRepository


def format_power(value):
    if value is None:
        return "-"

    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"

    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"

    return str(value)


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