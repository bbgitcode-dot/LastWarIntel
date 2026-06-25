"""
LastWarIntel
Module: Alliance Health CLI
Version: 1.0
"""

import argparse

from analytics.health.analyzer import AllianceHealthAnalyzer


def format_power(value):
    if value is None:
        return "-"

    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"

    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"

    return str(value)


def print_alliance_health(server: int):
    analyzer = AllianceHealthAnalyzer()
    results = analyzer.analyze(server)

    print()
    print(f"========== SERVER {server} ALLIANCE HEALTH ==========")
    print()
    print(f"{'Alliance':<10} {'Score':>5} {'Status':<10} {'Trend':<10} {'Risk':<6} {'Power':>18}")
    print("-" * 75)

    for item in results:
        first_power = item.facts.get("first_power")
        last_power = item.facts.get("last_power")
        power = f"{format_power(first_power)} → {format_power(last_power)}"

        print(
            f"{item.alliance:<10} "
            f"{item.score:>5} "
            f"{item.status:<10} "
            f"{item.trend:<10} "
            f"{item.risk:<6} "
            f"{power:>18}"
        )

        for reason in item.reasons:
            print(f"   - {reason}")

        print()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Show alliance health report for one server."
    )
    parser.add_argument("server", type=int)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print_alliance_health(args.server)