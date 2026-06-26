"""
LastWarIntel
Smoke Test
Ranking
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from analytics.ranking.facade import RankingFacade  # noqa: E402


def main() -> None:
    ranking = RankingFacade().analyze(638)

    assert ranking.recruitment.entries
    assert ranking.growth.entries

    recruitment = ranking.recruitment.entries

    for i in range(len(recruitment) - 1):
        assert recruitment[i].score >= recruitment[i + 1].score

    growth = ranking.growth.entries

    for i in range(len(growth) - 1):
        assert growth[i].score >= growth[i + 1].score

    print("PASS")


if __name__ == "__main__":
    main()