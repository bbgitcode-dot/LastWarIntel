"""
Smoke Test
Ranking Type Fallback
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from parser.ranking import infer_ranking_type_from_values  # noqa: E402


def main() -> None:
    assert infer_ranking_type_from_values(
        "unknown",
        [{"power": 1_250_000_000}],
    ) == "alliance_power"

    assert infer_ranking_type_from_values(
        "unknown",
        [{"power": 292_341_388}],
    ) == "total_hero_power"

    assert infer_ranking_type_from_values(
        "alliance_power",
        [{"power": 292_341_388}],
    ) == "alliance_power"

    assert infer_ranking_type_from_values(
        "unknown",
        [],
    ) == "unknown"

    print("PASS")


if __name__ == "__main__":
    main()
