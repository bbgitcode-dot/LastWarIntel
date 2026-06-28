"""
Smoke Test
Structured THP Parser
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from parser.player_ranking import (  # noqa: E402
    build_player_ranking_snapshot,
    split_alliance_tag_and_player_name,
)


def main() -> None:
    assert split_alliance_tag_and_player_name("[ACEv] Tarori") == ("ACEv", "Tarori")
    assert split_alliance_tag_and_player_name("Tarori") == (None, "Tarori")
    assert split_alliance_tag_and_player_name("([ACEv]  Tarori") == ("ACEv", "Tarori")
    assert split_alliance_tag_and_player_name("[ACEv| Tarori") == ("ACEv", "Tarori")

    snapshot = build_player_ranking_snapshot(
        rows=[
            {
                "name": "[ACEv] Tarori",
                "power": 292_341_388,
                "confidence": 0.91,
                "raw_text": "1 | [ACEv] Tarori | 292341388",
            },
            {
                "name": "NoAlliancePlayer",
                "power": 181_000_000,
                "confidence": 0.88,
            },
        ],
        server=573,
        snapshot_id="s573-thp-test",
        source_file="thp.png",
    )

    assert snapshot.server == 573
    assert snapshot.ranking_type == "total_hero_power"
    assert len(snapshot.entries) == 2

    first = snapshot.entries[0]
    assert first.rank == 1
    assert first.alliance_tag == "ACEv"
    assert first.player_name == "Tarori"
    assert first.hero_power == 292_341_388
    assert first.confidence == 0.91

    second = snapshot.entries[1]
    assert second.alliance_tag is None
    assert second.player_name == "NoAlliancePlayer"

    legacy = snapshot.to_legacy_rows()[0]
    assert legacy["name"] == "[ACEv] Tarori"
    assert legacy["player_name"] == "Tarori"
    assert legacy["alliance_tag"] == "ACEv"
    assert legacy["power"] == 292_341_388

    print("PASS")


if __name__ == "__main__":
    main()
