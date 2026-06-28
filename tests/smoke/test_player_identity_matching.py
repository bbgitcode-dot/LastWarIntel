"""Smoke Test
Player Identity Matching
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from analytics.matching.player_identity import PlayerIdentityMatcher  # noqa: E402
from models.player_ranking import PlayerRankingEntry, PlayerRankingSnapshot  # noqa: E402


def entry(
    name: str,
    power: int,
    alliance: str | None = "ACEv",
    server: int = 573,
    confidence: float = 1.0,
) -> PlayerRankingEntry:
    return PlayerRankingEntry(
        rank=1,
        server=server,
        alliance_tag=alliance,
        player_name=name,
        hero_power=power,
        confidence=confidence,
    )


def main() -> None:
    matcher = PlayerIdentityMatcher()

    same = matcher.match_entries(
        entry("Tarori", 292_341_388, "ACEv", confidence=1.0),
        entry("Tar0ri", 292_355_121, "ACEv", confidence=0.9),
    )
    assert same.decision == "match"
    assert same.score >= 85.0
    assert same.breakdown.name_similarity > 0.80
    assert same.breakdown.power_similarity > 0.95

    changed_alliance = matcher.match_entries(
        entry("Tarori", 292_341_388, "ACEv"),
        entry("Tarori", 300_000_000, "XYZ"),
    )
    assert changed_alliance.decision in {"match", "possible_match"}
    assert changed_alliance.breakdown.alliance_similarity == 0.0

    different = matcher.match_entries(
        entry("Tarori", 292_341_388, "ACEv"),
        entry("DarkWolf", 120_000_000, "XYZ"),
    )
    assert different.decision == "no_match"

    other_server = matcher.match_entries(
        entry("Tarori", 292_341_388, "ACEv", server=573),
        entry("Tarori", 292_341_388, "ACEv", server=638),
    )
    assert other_server.decision == "no_match"
    assert other_server.score == 0.0

    baseline_snapshot = PlayerRankingSnapshot(
        server=573,
        ranking_type="total_hero_power",
        entries=[
            entry("Tarori", 292_341_388, "ACEv"),
            entry("NoAlliancePlayer", 181_000_000, None),
        ],
    )
    current_snapshot = PlayerRankingSnapshot(
        server=573,
        ranking_type="total_hero_power",
        entries=[
            entry("Tar0ri", 292_355_121, "ACEv", confidence=0.9),
            entry("NewPlayer", 199_000_000, "NEW"),
        ],
    )

    snapshot_result = matcher.match_snapshots(baseline_snapshot, current_snapshot)
    assert len(snapshot_result.matches) == 1
    assert snapshot_result.matches[0].baseline.player_name == "Tarori"
    assert snapshot_result.matches[0].current.player_name == "Tar0ri"
    assert len(snapshot_result.unmatched_baseline) == 1
    assert len(snapshot_result.unmatched_current) == 1

    print("PASS")


if __name__ == "__main__":
    main()
