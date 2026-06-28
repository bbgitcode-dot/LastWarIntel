"""Filesystem repository for structured ranking snapshots.

This repository is intentionally small and deterministic. It gives OCR-derived
snapshots a stable identity before they are used by matching, difference
detection, or intelligence modules.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Literal, Optional

from models.player_ranking import PlayerRankingEntry, PlayerRankingSnapshot
from models.snapshot_identity import SnapshotKey, SnapshotRecord, SnapshotSaveResult

SnapshotSaveMode = Literal["skip", "replace", "revision"]


class SnapshotRepository:
    """Store and retrieve structured PlayerRankingSnapshot objects."""

    def __init__(self, root: str | Path = "data/snapshots") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def exists(self, key: SnapshotKey) -> bool:
        return self._metadata_path(key).exists()

    def latest(
        self,
        *,
        server: int,
        ranking_type: str,
        season: Optional[str] = None,
    ) -> Optional[SnapshotRecord]:
        records = self.history(server=server, ranking_type=ranking_type, season=season)
        return records[-1] if records else None

    def history(
        self,
        *,
        server: int,
        ranking_type: str,
        season: Optional[str] = None,
    ) -> list[SnapshotRecord]:
        records: list[SnapshotRecord] = []
        for metadata_path in self.root.glob("*/metadata.json"):
            record = self._read_record(metadata_path)
            if record.key.server != int(server):
                continue
            if record.key.ranking_type != ranking_type:
                continue
            if season is not None and record.key.season != season:
                continue
            records.append(record)

        return sorted(records, key=lambda record: (record.key.captured_date, record.revision))

    def save(
        self,
        snapshot: PlayerRankingSnapshot,
        *,
        season: Optional[str] = None,
        mode: SnapshotSaveMode = "skip",
    ) -> SnapshotSaveResult:
        """Save a snapshot using skip, replace, or revision behavior.

        * skip: keep existing data and return the existing record
        * replace: overwrite the logical snapshot revision 1
        * revision: create the next revision for the same logical key
        """
        if season is not None:
            snapshot.season = season

        key = snapshot.key()
        base_dir = self.root / key.canonical_id
        base_dir.mkdir(parents=True, exist_ok=True)

        existing = self._read_record(self._metadata_path(key)) if self.exists(key) else None

        if existing and mode == "skip":
            return SnapshotSaveResult(
                action="skipped",
                record=existing,
                path=str(self._snapshot_path(key, existing.revision)),
            )

        if mode == "replace":
            revision = 1
            action = "replaced" if existing else "created"
        elif mode == "revision":
            revision = self._next_revision(key)
            action = "revision_created" if existing else "created"
        else:
            revision = 1
            action = "created"

        snapshot_id = self._snapshot_id(key, revision)
        snapshot.snapshot_id = snapshot_id
        for entry in snapshot.entries:
            entry.snapshot_id = snapshot_id

        snapshot_path = self._snapshot_path(key, revision)
        snapshot_path.write_text(
            json.dumps(self._snapshot_to_dict(snapshot), indent=2, sort_keys=True),
            encoding="utf-8",
        )

        record = SnapshotRecord(
            key=key,
            snapshot_id=snapshot_id,
            revision=revision,
            created_at=datetime.now(timezone.utc),
            source_file=snapshot.source_file,
        )
        self._metadata_path(key).write_text(
            json.dumps(self._record_to_dict(record), indent=2, sort_keys=True),
            encoding="utf-8",
        )

        return SnapshotSaveResult(action=action, record=record, path=str(snapshot_path))

    def load(self, key: SnapshotKey, *, revision: Optional[int] = None) -> PlayerRankingSnapshot:
        if revision is None:
            if not self.exists(key):
                raise FileNotFoundError(key.canonical_id)
            revision = self._read_record(self._metadata_path(key)).revision

        path = self._snapshot_path(key, revision)
        data = json.loads(path.read_text(encoding="utf-8"))
        return self._snapshot_from_dict(data)

    def _snapshot_path(self, key: SnapshotKey, revision: int) -> Path:
        return self.root / key.canonical_id / f"snapshot_v{revision}.json"

    def _metadata_path(self, key: SnapshotKey) -> Path:
        return self.root / key.canonical_id / "metadata.json"

    def _next_revision(self, key: SnapshotKey) -> int:
        revisions = []
        for path in (self.root / key.canonical_id).glob("snapshot_v*.json"):
            stem = path.stem.replace("snapshot_v", "")
            if stem.isdigit():
                revisions.append(int(stem))
        return (max(revisions) + 1) if revisions else 1

    @staticmethod
    def _snapshot_id(key: SnapshotKey, revision: int) -> str:
        return f"{key.canonical_id}__v{revision}"

    @staticmethod
    def _snapshot_to_dict(snapshot: PlayerRankingSnapshot) -> dict:
        return {
            "snapshot_id": snapshot.snapshot_id,
            "season": snapshot.season,
            "server": snapshot.server,
            "ranking_type": snapshot.ranking_type,
            "created_at": snapshot.created_at.isoformat(),
            "source_file": snapshot.source_file,
            "entries": [asdict(entry) for entry in snapshot.entries],
        }

    @staticmethod
    def _snapshot_from_dict(data: dict) -> PlayerRankingSnapshot:
        entries = [PlayerRankingEntry(**entry) for entry in data.get("entries", [])]
        created_at = datetime.fromisoformat(data["created_at"])
        return PlayerRankingSnapshot(
            server=int(data["server"]),
            ranking_type=data["ranking_type"],
            entries=entries,
            snapshot_id=data.get("snapshot_id"),
            created_at=created_at,
            source_file=data.get("source_file"),
            season=data.get("season", "unknown"),
        )

    @staticmethod
    def _record_to_dict(record: SnapshotRecord) -> dict:
        return {
            "season": record.key.season,
            "server": record.key.server,
            "ranking_type": record.key.ranking_type,
            "captured_date": record.key.captured_date.isoformat(),
            "snapshot_id": record.snapshot_id,
            "revision": record.revision,
            "created_at": record.created_at.isoformat(),
            "source_file": record.source_file,
        }

    @staticmethod
    def _read_record(metadata_path: Path) -> SnapshotRecord:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
        key = SnapshotKey(
            season=data["season"],
            server=int(data["server"]),
            ranking_type=data["ranking_type"],
            captured_date=datetime.fromisoformat(data["captured_date"]).date(),
        )
        return SnapshotRecord(
            key=key,
            snapshot_id=data["snapshot_id"],
            revision=int(data["revision"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            source_file=data.get("source_file"),
        )
