"""Smoke Test
Matching Facade Player Identity API
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from analytics.matching.facade import MatchingFacade  # noqa: E402
from models.player_ranking import PlayerRankingEntry  # noqa: E402


def main() -> None:
    baseline = PlayerRankingEntry(
        rank=1,
        server=573,
        alliance_tag="ACEv",
        player_name="Tarori",
        hero_power=292_341_388,
        confidence=1.0,
    )
    current = PlayerRankingEntry(
        rank=1,
        server=573,
        alliance_tag="ACEv",
        player_name="Tar0ri",
        hero_power=292_355_121,
        confidence=0.9,
    )

    result = MatchingFacade().match_player_entries(baseline, current)

    assert result.decision == "match"
    assert result.score >= 85.0

    print("PASS")


if __name__ == "__main__":
    main()
