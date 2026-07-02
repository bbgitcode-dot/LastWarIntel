from pathlib import Path

from application.command_center.service import CommandCenterService
from application.snapshots.service import SnapshotService


def test_snapshot_service_creates_and_activates_named_context(tmp_path: Path):
    service = SnapshotService(storage_path=tmp_path / "data" / "managed_snapshots.json")

    created = service.create_snapshot(
        name="S6 pre Transfer",
        snapshot_type="screenshot_upload",
        description="Current screenshot upload batch",
        expected_rankings=["alliance_power", "total_hero_power"],
    )
    dashboard = service.get_dashboard()

    assert dashboard.has_active is True
    assert dashboard.active is not None
    assert dashboard.active.id == created.id
    assert dashboard.active.name == "S6 pre Transfer"
    assert dashboard.active.expected_rankings == ["alliance_power", "total_hero_power"]
    assert dashboard.open_count == 1


def test_command_center_exposes_active_snapshot(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    snapshot_service = SnapshotService(storage_path=tmp_path / "data" / "managed_snapshots.json")
    snapshot_service.create_snapshot(name="S6 pre Transfer", snapshot_type="screenshot_upload")

    command = CommandCenterService(database_path=tmp_path / "data" / "lastwarintel.sqlite").get_command_center()

    assert command.active_snapshot is not None
    assert command.active_snapshot.name == "S6 pre Transfer"
    assert command.active_snapshot.snapshot_type == "screenshot_upload"
