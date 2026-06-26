"""
LastWarIntel
Smoke Test
Situation
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from analytics.application.entity_report_builder import (  # noqa: E402
    EntityReportBuilder,
)


def main() -> None:
    report = EntityReportBuilder().build(638, "gjp")

    assert report.situation is not None
    assert report.situation.situation.findings

    print("PASS")


if __name__ == "__main__":
    main()