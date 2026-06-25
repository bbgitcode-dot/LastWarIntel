"""
LastWarIntel
Module: Alliance Events CLI
Version: 1.0

Command line interface for alliance event analysis.
"""

import argparse

from analytics.events.analyzer import AllianceEventAnalyzer
from analytics.events.formatter import AllianceEventFormatter


def print_alliance_events(server: int):
    analyzer = AllianceEventAnalyzer()
    formatter = AllianceEventFormatter()

    events = analyzer.analyze(server)
    report = formatter.format(server, events)

    print(report)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Show detected alliance events for a server."
    )
    parser.add_argument("server", type=int)

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print_alliance_events(args.server)