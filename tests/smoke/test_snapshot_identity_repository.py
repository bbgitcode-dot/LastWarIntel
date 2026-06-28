"""Smoke Test
Snapshot Identity Repository
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from models.player_ranking import PlayerRankingEntry, PlayerRankingSnapshot  # noqa: E402
from models.snapshot_identity import SnapshotKey  # noqa: E402
from services.snapshot_repository import SnapshotRepository  # noqa: E402


def build_snapshot(power: int = 292_341_388) -> PlayerRankingSnapshot:
    return PlayerRankingSnapshot(
        season="S6",
        server=573,
        ranking_type="total_hero_power",
        created_at=datetime(2026, 6, 28, 12, 0, tzinfo=timezone.utc),
        source_file="573-thp.png",
        entries=[
            PlayerRankingEntry(
                rank=1,
                server=573,
                alliance_tag="ACEv",
                player_name="Tarori",
                hero_power=power,
                confidence=0.97,
            )
        ],
    )


def main() -> None:
    root = ROOT / "tmp" / "snapshot_repository_smoke"
    if root.exists():
        shutil.rmtree(root)

    repository = SnapshotRepository(root=root)
    snapshot = build_snapshot()

    key = snapshot.key()
    assert key == SnapshotKey.from_datetime(
        season="S6",
        server=573,
        ranking_type="total_hero_power",
        captured_at=datetime(2026, 6, 28, 12, 0, tzinfo=timezone.utc),
    )
    assert key.canonical_id == "S6__s573__total_hero_power__2026-06-28"
    assert repository.exists(key) is False

    created = repository.save(snapshot, mode="skip")
    assert created.action == "created"
    assert created.record.revision == 1
    assert repository.exists(key) is True
    assert snapshot.snapshot_id == "S6__s573__total_hero_power__2026-06-28__v1"
    assert snapshot.entries[0].snapshot_id == snapshot.snapshot_id

    skipped = repository.save(build_snapshot(power=300_000_000), mode="skip")
    assert skipped.action == "skipped"
    assert skipped.record.revision == 1
    loaded = repository.load(key)
    assert loaded.entries[0].hero_power == 292_341_388

    revised = repository.save(build_snapshot(power=300_000_000), mode="revision")
    assert revised.action == "revision_created"
    assert revised.record.revision == 2
    loaded_latest = repository.load(key)
    assert loaded_latest.entries[0].hero_power == 300_000_000

    replaced = repository.save(build_snapshot(power=301_000_000), mode="replace")
    assert replaced.action == "replaced"
    assert replaced.record.revision == 1
    loaded_replaced = repository.load(key)
    assert loaded_replaced.entries[0].hero_power == 301_000_000

    history = repository.history(server=573, ranking_type="total_hero_power", season="S6")
    assert len(history) == 1
    assert history[0].snapshot_id.endswith("__v1")
    assert repository.latest(server=573, ranking_type="total_hero_power", season="S6") is not None

    shutil.rmtree(root)
    print("PASS")


if __name__ == "__main__":
    main()
