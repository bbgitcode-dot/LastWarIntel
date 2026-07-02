from pathlib import Path

import pytest

from application.snapshots.service import SnapshotContextError, SnapshotService
from services.command_center import generate_command_center


def test_screenshot_import_requires_active_snapshot(tmp_path: Path):
    service = SnapshotService(storage_path=tmp_path / "data" / "managed_snapshots.json")

    with pytest.raises(SnapshotContextError):
        service.require_active_import_snapshot()


def test_import_report_binds_to_active_snapshot_and_reports_missing_feeds(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    service = SnapshotService(storage_path=tmp_path / "data" / "managed_snapshots.json")
    snapshot = service.create_snapshot(
        name="S6 pre Transfer",
        expected_rankings=["alliance_power", "total_hero_power"],
        assigned_servers=[549, 550],
    )

    report = service.bind_import_report(
        {
            "schema": "sentinel.import_run.v1",
            "created_at": "2026-07-03T10:00:00+00:00",
            "output_file": "output/snapshots/example/lastwar_export.xlsx",
            "imports": [
                {"server": 549, "ranking_type": "alliance_power", "rows": 10, "screenshots": 1, "status": "Ready"},
                {"server": 549, "ranking_type": "total_hero_power", "rows": 10, "screenshots": 1, "status": "Ready"},
            ],
        },
        snapshot,
    )
    Path("data").mkdir(exist_ok=True)
    Path("data/latest_import_report.json").write_text(__import__("json").dumps(report), encoding="utf-8")

    coverage = service.get_coverage(snapshot)

    assert coverage.is_bound is True
    assert coverage.bound_snapshot_id == snapshot.id
    assert coverage.imported_servers == [549]
    assert {(item.server, item.ranking_type) for item in coverage.missing_feeds} == {
        (550, "alliance_power"),
        (550, "total_hero_power"),
    }


def test_review_history_entries_keep_snapshot_binding(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    service = SnapshotService(storage_path=tmp_path / "data" / "managed_snapshots.json")
    snapshot = service.create_snapshot(name="S6 pre Transfer")
    report = service.bind_import_report(
        {
            "schema": "sentinel.import_run.v1",
            "created_at": "2026-07-03T10:00:00+00:00",
            "status": "Review",
            "readiness": 90,
            "review_item_count": 1,
            "reviews": [
                {
                    "server": 549,
                    "ranking_type": "alliance_power",
                    "rank": 1,
                    "title": "Data Guard quarantine",
                    "reason": "data_guard_quarantine",
                    "description": "review needed",
                    "screenshot": "s1.png",
                }
            ],
        },
        snapshot,
    )
    Path("data").mkdir(exist_ok=True)
    Path("data/latest_import_report.json").write_text(__import__("json").dumps(report), encoding="utf-8")

    result = generate_command_center()
    history = __import__("json").loads(Path(result["review_history_store"]).read_text(encoding="utf-8"))

    assert history["items"][0]["snapshot_id"] == snapshot.id
    assert history["items"][0]["snapshot_name"] == "S6 pre Transfer"
