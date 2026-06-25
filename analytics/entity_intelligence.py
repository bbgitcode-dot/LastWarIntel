"""
LastWarIntel
Entity Intelligence CLI
Version: 2.0

Console entry point for alliance intelligence.
"""

from __future__ import annotations

import argparse

from analytics.application.entity_report_builder import EntityReportBuilder
from analytics.application.entity_report_renderer import EntityReportRenderer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Alliance Intelligence Report"
    )

    parser.add_argument(
        "server",
        type=int,
        help="Server number",
    )

    parser.add_argument(
        "alliance",
        type=str,
        help="Alliance tag",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    report = EntityReportBuilder().build(
        server=args.server,
        alliance=args.alliance,
    )

    EntityReportRenderer().render(report)


if __name__ == "__main__":
    main()