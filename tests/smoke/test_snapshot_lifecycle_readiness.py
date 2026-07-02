from pathlib import Path

import pytest

from application.snapshots.service import SnapshotContextError, SnapshotService


def test_snapshot_lifecycle_locks_verified_snapshot(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    service = SnapshotService(Path("data/managed_snapshots.json"))
    snapshot = service.create_snapshot(
        name="Lifecycle Test",
        server_scope_mode="range",
        server_range_start="549",
        server_range_end="550",
    )

    assert snapshot.status == "open"
    assert len(snapshot.assigned_servers) == 2
    service.update_status(snapshot.id, "collecting")
    verified = service.update_status(snapshot.id, "verified")

    assert verified is not None
    assert verified.locked is True
    with pytest.raises(SnapshotContextError):
        service.update_snapshot(verified.id, description="should be blocked")


def test_snapshot_status_aliases_and_completion_report(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    service = SnapshotService(Path("data/managed_snapshots.json"))
    snapshot = service.create_snapshot(name="Alias Test", assigned_servers="549", server_scope_mode="selected")

    collecting = service.update_status(snapshot.id, "importing")
    assert collecting is not None
    assert collecting.status == "collecting"
    verified = service.update_status(snapshot.id, "complete")
    assert verified is not None
    assert verified.status == "verified"

    report = Path("reports/snapshots") / verified.id / "completion_report.json"
    assert report.exists()
