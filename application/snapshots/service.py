"""JSON-backed managed snapshot service.

This is the first foundation layer for import context management.  It avoids
changing Operational Truth or historical SQLite records directly; it only stores
an auditable, human-chosen context for future screenshot uploads and review
workflows.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .models import ManagedSnapshot, SnapshotDashboard

DEFAULT_EXPECTED_RANKINGS = ["alliance_power", "total_hero_power"]
ALLOWED_TYPES = {"screenshot_upload", "historical_excel", "manual_import"}
ALLOWED_STATUSES = {"open", "importing", "review", "complete", "closed"}


class SnapshotService:
    """Manage human-named import snapshots in data/managed_snapshots.json."""

    def __init__(self, storage_path: Path | None = None) -> None:
        self.storage_path = storage_path or Path("data/managed_snapshots.json")

    def get_dashboard(self) -> SnapshotDashboard:
        payload = self._load()
        snapshots = [self._from_raw(item) for item in payload.get("snapshots", []) if isinstance(item, dict)]
        active_id = str(payload.get("active_snapshot_id") or "")
        active = next((item for item in snapshots if item.id == active_id), None)
        open_count = len([item for item in snapshots if item.status in {"open", "importing", "review"}])
        return SnapshotDashboard(
            has_active=active is not None,
            active=active,
            snapshots=sorted(snapshots, key=lambda item: item.created_at, reverse=True),
            open_count=open_count,
            total_count=len(snapshots),
            storage_path=str(self.storage_path),
        )

    def create_snapshot(
        self,
        *,
        name: str,
        snapshot_type: str = "screenshot_upload",
        description: str = "",
        expected_rankings: list[str] | None = None,
        source: str = "",
        set_active: bool = True,
    ) -> ManagedSnapshot:
        clean_name = self._clean_name(name)
        clean_type = snapshot_type if snapshot_type in ALLOWED_TYPES else "screenshot_upload"
        rankings = self._clean_rankings(expected_rankings or DEFAULT_EXPECTED_RANKINGS)
        now = self._now()
        snapshot = ManagedSnapshot(
            id=self._slug_id(clean_name),
            name=clean_name,
            snapshot_type=clean_type,
            status="open",
            description=description.strip(),
            expected_rankings=rankings,
            created_at=now,
            updated_at=now,
            source=source.strip(),
            assigned_servers=[],
        )
        payload = self._load()
        existing = [item for item in payload.get("snapshots", []) if isinstance(item, dict)]
        existing = [item for item in existing if str(item.get("id")) != snapshot.id]
        existing.append(asdict(snapshot))
        payload["snapshots"] = existing
        if set_active:
            payload["active_snapshot_id"] = snapshot.id
        self._save(payload)
        return snapshot

    def set_active(self, snapshot_id: str) -> ManagedSnapshot | None:
        payload = self._load()
        snapshots = [item for item in payload.get("snapshots", []) if isinstance(item, dict)]
        match = next((item for item in snapshots if str(item.get("id")) == snapshot_id), None)
        if not match:
            return None
        payload["active_snapshot_id"] = snapshot_id
        self._save(payload)
        return self._from_raw(match)

    def update_status(self, snapshot_id: str, status: str) -> ManagedSnapshot | None:
        clean_status = status if status in ALLOWED_STATUSES else "open"
        payload = self._load()
        changed: dict | None = None
        for item in payload.get("snapshots", []) or []:
            if isinstance(item, dict) and str(item.get("id")) == snapshot_id:
                item["status"] = clean_status
                item["updated_at"] = self._now()
                changed = item
                break
        if not changed:
            return None
        self._save(payload)
        return self._from_raw(changed)

    def _load(self) -> dict:
        if not self.storage_path.exists():
            return {"active_snapshot_id": "", "snapshots": []}
        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"active_snapshot_id": "", "snapshots": []}
        if not isinstance(payload, dict):
            return {"active_snapshot_id": "", "snapshots": []}
        payload.setdefault("active_snapshot_id", "")
        payload.setdefault("snapshots", [])
        return payload

    def _save(self, payload: dict) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _from_raw(raw: dict) -> ManagedSnapshot:
        servers: list[int] = []
        for value in raw.get("assigned_servers", []) or []:
            try:
                servers.append(int(value))
            except (TypeError, ValueError):
                continue
        rankings = SnapshotService._clean_rankings(raw.get("expected_rankings", []) or DEFAULT_EXPECTED_RANKINGS)
        return ManagedSnapshot(
            id=str(raw.get("id") or ""),
            name=str(raw.get("name") or "Unnamed Snapshot"),
            snapshot_type=str(raw.get("snapshot_type") or "screenshot_upload"),
            status=str(raw.get("status") or "open"),
            description=str(raw.get("description") or ""),
            expected_rankings=rankings,
            created_at=str(raw.get("created_at") or ""),
            updated_at=str(raw.get("updated_at") or ""),
            source=str(raw.get("source") or ""),
            assigned_servers=sorted(set(servers)),
        )

    @staticmethod
    def _clean_name(name: str) -> str:
        value = (name or "").strip()
        if not value:
            raise ValueError("Snapshot name is required")
        if len(value) > 80:
            value = value[:80].strip()
        return value

    @staticmethod
    def _clean_rankings(values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            normalized = str(value or "").strip().lower().replace(" ", "_")
            if normalized and normalized not in cleaned:
                cleaned.append(normalized)
        return cleaned or list(DEFAULT_EXPECTED_RANKINGS)

    @staticmethod
    def _slug_id(name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "snapshot"
        return f"{slug}-{uuid4().hex[:8]}"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
