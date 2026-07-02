"""JSON-backed managed snapshot service.

Managed snapshots are the mandatory import context for screenshot batches.
v0.9.5.75 adds a lifecycle, operational readiness, completion reports and an
append-only audit trail so a snapshot can become a reproducible Operational
Truth candidate without mixing phases.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .models import (
    ManagedSnapshot,
    ServerScope,
    SnapshotAuditEntry,
    SnapshotCoverage,
    SnapshotDashboard,
    SnapshotFeedCoverage,
    SnapshotMissingFeed,
    SnapshotReadiness,
)

DEFAULT_EXPECTED_RANKINGS = ["alliance_power", "total_hero_power"]
ALLOWED_TYPES = {"screenshot_upload", "historical_excel", "manual_import"}
LIFECYCLE_STATUSES = {"open", "collecting", "reviewing", "verified", "locked", "archived"}
STATUS_ALIASES = {
    "importing": "collecting",
    "review": "reviewing",
    "complete": "verified",
    "closed": "locked",
}
ACTIVE_IMPORT_STATUSES = {"open", "collecting"}
EDITABLE_STATUSES = {"open", "collecting"}
REVIEWABLE_STATUSES = {"collecting", "reviewing"}
LOCKED_STATUSES = {"verified", "locked", "archived"}
SERVER_SCOPE_MODES = {"all", "range", "selected"}
REPORT_ROOT = Path("reports/snapshots")


class SnapshotContextError(RuntimeError):
    """Raised when a screenshot import has no safe active snapshot context."""


class SnapshotService:
    """Manage human-named import snapshots in data/managed_snapshots.json."""

    def __init__(self, storage_path: Path | None = None) -> None:
        self.storage_path = storage_path or Path("data/managed_snapshots.json")

    def get_dashboard(self) -> SnapshotDashboard:
        payload = self._load()
        snapshots = [self._from_raw(item) for item in payload.get("snapshots", []) if isinstance(item, dict)]
        active_id = str(payload.get("active_snapshot_id") or "")
        active = next((item for item in snapshots if item.id == active_id), None)
        open_count = len([item for item in snapshots if item.status in ACTIVE_IMPORT_STATUSES | REVIEWABLE_STATUSES])
        coverage = self.get_coverage(active) if active else None
        readiness = self.get_readiness(active, coverage) if active else None
        return SnapshotDashboard(
            has_active=active is not None,
            active=active,
            snapshots=sorted(snapshots, key=lambda item: item.created_at, reverse=True),
            open_count=open_count,
            total_count=len(snapshots),
            storage_path=str(self.storage_path),
            active_coverage=coverage,
            active_readiness=readiness,
        )

    def get_active_snapshot(self) -> ManagedSnapshot | None:
        return self.get_dashboard().active

    def require_active_import_snapshot(self) -> ManagedSnapshot:
        snapshot = self.get_active_snapshot()
        if snapshot is None:
            raise SnapshotContextError(
                "No active Sentinel snapshot selected. Create or activate a screenshot_upload snapshot in the Import Center before running screenshot import."
            )
        if snapshot.snapshot_type != "screenshot_upload":
            raise SnapshotContextError(
                f"Active snapshot '{snapshot.name}' is type '{snapshot.snapshot_type}', not 'screenshot_upload'. Activate a screenshot upload snapshot before importing screenshots."
            )
        if snapshot.status not in ACTIVE_IMPORT_STATUSES:
            raise SnapshotContextError(
                f"Active snapshot '{snapshot.name}' is '{snapshot.status}'. Only OPEN or COLLECTING snapshots accept screenshot imports."
            )
        return snapshot

    def snapshot_output_dir(self, snapshot: ManagedSnapshot | None = None) -> Path:
        active = snapshot or self.require_active_import_snapshot()
        return Path("output") / "snapshots" / active.id

    def create_snapshot(
        self,
        *,
        name: str,
        snapshot_type: str = "screenshot_upload",
        description: str = "",
        expected_rankings: list[str] | None = None,
        source: str = "",
        assigned_servers: list[int] | str | None = None,
        server_scope_mode: str = "selected",
        server_range_start: int | str | None = None,
        server_range_end: int | str | None = None,
        set_active: bool = True,
    ) -> ManagedSnapshot:
        clean_name = self._clean_name(name)
        clean_type = snapshot_type if snapshot_type in ALLOWED_TYPES else "screenshot_upload"
        rankings = self._clean_rankings(expected_rankings or DEFAULT_EXPECTED_RANKINGS)
        server_scope = self._build_server_scope(
            mode=server_scope_mode,
            assigned_servers=assigned_servers or [],
            server_range_start=server_range_start,
            server_range_end=server_range_end,
        )
        servers = self._expand_server_scope(server_scope)
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
            assigned_servers=servers,
            server_scope=server_scope,
            locked=False,
            audit=[SnapshotAuditEntry(event="created", at=now, detail="Snapshot created from Import Center")],
        )
        payload = self._load()
        existing = [item for item in payload.get("snapshots", []) if isinstance(item, dict)]
        existing = [item for item in existing if str(item.get("id")) != snapshot.id]
        raw = asdict(snapshot)
        existing.append(raw)
        payload["snapshots"] = existing
        if set_active:
            payload["active_snapshot_id"] = snapshot.id
            self._append_audit(raw, "activated", detail="Set active at creation")
        self._save(payload)
        return self._from_raw(raw)

    def set_active(self, snapshot_id: str) -> ManagedSnapshot | None:
        payload = self._load()
        snapshots = [item for item in payload.get("snapshots", []) if isinstance(item, dict)]
        match = next((item for item in snapshots if str(item.get("id")) == snapshot_id), None)
        if not match:
            return None
        payload["active_snapshot_id"] = snapshot_id
        self._append_audit(match, "activated", detail="Set active snapshot context")
        self._save(payload)
        return self._from_raw(match)

    def update_status(self, snapshot_id: str, status: str) -> ManagedSnapshot | None:
        clean_status = self._normalize_status(status)
        payload = self._load()
        changed: dict | None = None
        for item in payload.get("snapshots", []) or []:
            if isinstance(item, dict) and str(item.get("id")) == snapshot_id:
                current = self._normalize_status(str(item.get("status") or "open"))
                if current == "archived" and clean_status != "archived":
                    raise SnapshotContextError("Archived snapshots are read-only and cannot be reopened.")
                if current == "locked" and clean_status not in {"locked", "archived"}:
                    raise SnapshotContextError("Locked snapshots cannot be moved back to an editable state.")
                before = current
                item["status"] = clean_status
                item["updated_at"] = self._now()
                self._append_audit(item, f"status_{before}_to_{clean_status}", detail=f"Status changed from {before} to {clean_status}")
                changed = item
                break
        if not changed:
            return None
        self._save(payload)
        snapshot = self._from_raw(changed)
        if snapshot.status in {"verified", "locked"}:
            self.write_completion_report(snapshot)
        return snapshot

    def verify_snapshot(self, snapshot_id: str) -> ManagedSnapshot | None:
        snapshot = self.update_status(snapshot_id, "verified")
        return snapshot

    def lock_snapshot(self, snapshot_id: str) -> ManagedSnapshot | None:
        snapshot = self.update_status(snapshot_id, "locked")
        return snapshot

    def update_snapshot(
        self,
        snapshot_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        expected_rankings: list[str] | None = None,
        server_scope_mode: str | None = None,
        assigned_servers: list[int] | str | None = None,
        server_range_start: int | str | None = None,
        server_range_end: int | str | None = None,
    ) -> ManagedSnapshot | None:
        payload = self._load()
        changed: dict | None = None
        for item in payload.get("snapshots", []) or []:
            if not isinstance(item, dict) or str(item.get("id")) != snapshot_id:
                continue
            if self._normalize_status(str(item.get("status") or "open")) not in EDITABLE_STATUSES:
                raise SnapshotContextError("Snapshot is locked for editing. Only OPEN or COLLECTING snapshots can be edited.")
            before = dict(item)
            if name is not None:
                item["name"] = self._clean_name(name)
            if description is not None:
                item["description"] = description.strip()
            if expected_rankings is not None:
                item["expected_rankings"] = self._clean_rankings(expected_rankings)
            if server_scope_mode is not None:
                scope = self._build_server_scope(
                    mode=server_scope_mode,
                    assigned_servers=assigned_servers or [],
                    server_range_start=server_range_start,
                    server_range_end=server_range_end,
                )
                item["server_scope"] = asdict(scope)
                item["assigned_servers"] = self._expand_server_scope(scope)
            item["updated_at"] = self._now()
            self._append_audit(item, "snapshot_updated", before=before, detail="Editable snapshot fields changed")
            changed = item
            break
        if not changed:
            return None
        self._save(payload)
        return self._from_raw(changed)

    def bind_import_report(self, report: dict[str, Any], snapshot: ManagedSnapshot) -> dict[str, Any]:
        bound = dict(report or {})
        previous = bound.get("snapshot") if isinstance(bound.get("snapshot"), dict) else {}
        if previous and previous.get("id") and previous.get("id") != snapshot.id:
            bound["snapshot_binding_warning"] = "report_rebound_to_different_snapshot"
        bound["snapshot"] = self._snapshot_binding(snapshot)
        bound["snapshot_id"] = snapshot.id
        bound["snapshot_name"] = snapshot.name
        bound["snapshot_type"] = snapshot.snapshot_type
        bound["snapshot_status_at_import"] = snapshot.status
        bound["snapshot_expected_rankings"] = list(snapshot.expected_rankings)
        bound["snapshot_expected_servers"] = list(snapshot.assigned_servers)
        bound["snapshot_server_scope"] = asdict(snapshot.server_scope)
        bound["schema"] = "sentinel.import_run.v3"
        bound["schema_previous"] = report.get("schema") if isinstance(report, dict) else None
        return bound

    def mirror_export_to_snapshot(self, output_file: str, snapshot: ManagedSnapshot) -> str:
        source = Path(output_file)
        if not source.exists():
            return ""
        target_dir = self.snapshot_output_dir(snapshot)
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / source.name
        try:
            if source.resolve() != target.resolve():
                shutil.copy2(source, target)
        except OSError:
            return ""
        return str(target)

    def get_coverage(self, snapshot: ManagedSnapshot | None = None) -> SnapshotCoverage:
        active = snapshot or self.get_active_snapshot()
        report = self._load_json(Path("data/latest_import_report.json"))
        history = self._load_json(Path("data/review_history.json"))
        binding = report.get("snapshot") if isinstance(report.get("snapshot"), dict) else {}
        bound_id = str(binding.get("id") or report.get("snapshot_id") or "")
        bound_name = str(binding.get("name") or report.get("snapshot_name") or "")
        is_bound = bool(active and bound_id == active.id)

        imported_feeds: list[SnapshotFeedCoverage] = []
        imported_servers: set[int] = set()
        imported_rankings: set[str] = set()
        if is_bound:
            for item in report.get("imports") or []:
                if not isinstance(item, dict):
                    continue
                server = self._optional_int(item.get("server"))
                ranking = self._clean_ranking(str(item.get("ranking_type") or "unknown"))
                if server:
                    imported_servers.add(server)
                if ranking:
                    imported_rankings.add(ranking)
                imported_feeds.append(
                    SnapshotFeedCoverage(
                        server=server,
                        ranking_type=ranking or "unknown",
                        rows=self._int(item.get("rows")),
                        screenshots=self._int(item.get("screenshots")),
                        status=str(item.get("status") or "Unknown"),
                        source=str(item.get("source") or ""),
                    )
                )

        expected_rankings = list(active.expected_rankings) if active else list(DEFAULT_EXPECTED_RANKINGS)
        expected_servers = self._expected_servers_for_snapshot(active, report) if active else []
        missing: list[SnapshotMissingFeed] = []
        if active and expected_servers:
            present = {(feed.server, feed.ranking_type) for feed in imported_feeds if feed.server}
            for server in expected_servers:
                for ranking in expected_rankings:
                    if (server, ranking) not in present:
                        missing.append(SnapshotMissingFeed(server=server, ranking_type=ranking, reason="expected_feed_missing"))
        elif active:
            for ranking in expected_rankings:
                if ranking not in imported_rankings:
                    missing.append(SnapshotMissingFeed(server=None, ranking_type=ranking, reason="expected_ranking_not_seen"))

        open_reviews = 0
        if active:
            for item in history.get("items") or []:
                if not isinstance(item, dict) or str(item.get("status") or "").upper() != "OPEN":
                    continue
                item_snapshot = item.get("snapshot") if isinstance(item.get("snapshot"), dict) else {}
                if str(item_snapshot.get("id") or item.get("snapshot_id") or "") == active.id:
                    open_reviews += 1

        warning = ""
        if active and report and not is_bound:
            warning = "Latest import report is not bound to the active snapshot. Do not treat it as current phase evidence."

        expected_feed_count = len(expected_servers) * len(expected_rankings) if expected_servers else len(expected_rankings)
        imported_valid_feed_count = len({(feed.server, feed.ranking_type) for feed in imported_feeds if feed.server and feed.ranking_type in expected_rankings})
        if not expected_servers:
            imported_valid_feed_count = len([ranking for ranking in expected_rankings if ranking in imported_rankings])
        completeness_percent = round((imported_valid_feed_count / expected_feed_count) * 100, 1) if expected_feed_count else 0.0

        return SnapshotCoverage(
            snapshot=active,
            is_bound=is_bound,
            bound_snapshot_id=bound_id,
            bound_snapshot_name=bound_name,
            report_created_at=str(report.get("created_at") or ""),
            expected_rankings=expected_rankings,
            expected_servers=expected_servers,
            expected_feed_count=expected_feed_count,
            imported_valid_feed_count=imported_valid_feed_count,
            completeness_percent=completeness_percent,
            imported_servers=sorted(imported_servers),
            imported_rankings=sorted(imported_rankings),
            imported_feeds=imported_feeds,
            missing_feeds=missing,
            open_review_count=open_reviews,
            output_file=str(report.get("snapshot_export_file") or report.get("output_file") or ""),
            warning=warning,
        )

    def get_readiness(self, snapshot: ManagedSnapshot | None = None, coverage: SnapshotCoverage | None = None) -> SnapshotReadiness:
        active = snapshot or self.get_active_snapshot()
        cov = coverage or self.get_coverage(active)
        report = self._load_json(Path("data/latest_import_report.json"))
        data_guard = report.get("data_guard") if isinstance(report.get("data_guard"), dict) else {}
        data_guard_status = str(data_guard.get("status") or report.get("status") or "").lower()
        ranking_recovery = report.get("ranking_recovery") if isinstance(report.get("ranking_recovery"), dict) else {}
        rejected = self._int(ranking_recovery.get("rejected"))

        expected_feeds_ok = cov.expected_feed_count > 0
        completeness_ok = cov.expected_feed_count > 0 and cov.imported_valid_feed_count >= cov.expected_feed_count and not cov.missing_feeds
        reviews_ok = cov.open_review_count == 0
        data_guard_ok = not data_guard_status or data_guard_status in {"pass", "ok", "success", "ready", "verified"}
        ranking_guard_ok = rejected == 0
        bound_ok = cov.is_bound and not cov.warning
        operational_truth_ready = bool(active) and expected_feeds_ok and completeness_ok and reviews_ok and data_guard_ok and ranking_guard_ok and bound_ok
        message = "READY FOR OPERATIONAL TRUTH" if operational_truth_ready else "NOT READY - resolve missing feeds, reviews or guard warnings first"
        return SnapshotReadiness(
            status=active.status if active else "none",
            operational_truth_ready=operational_truth_ready,
            expected_feeds_ok=expected_feeds_ok,
            completeness_ok=completeness_ok,
            reviews_ok=reviews_ok,
            data_guard_ok=data_guard_ok,
            ranking_guard_ok=ranking_guard_ok,
            locked=bool(active and active.locked),
            missing_feed_count=len(cov.missing_feeds),
            open_review_count=cov.open_review_count,
            validated_feed_count=cov.imported_valid_feed_count,
            expected_feed_count=cov.expected_feed_count,
            completeness_percent=cov.completeness_percent,
            message=message,
        )

    def write_completion_report(self, snapshot: ManagedSnapshot, coverage: SnapshotCoverage | None = None) -> str:
        cov = coverage or self.get_coverage(snapshot)
        readiness = self.get_readiness(snapshot, cov)
        report_dir = REPORT_ROOT / snapshot.id
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / "completion_report.json"
        payload = {
            "schema": "sentinel.snapshot_completion.v1",
            "created_at": self._now(),
            "snapshot": {
                "id": snapshot.id,
                "name": snapshot.name,
                "type": snapshot.snapshot_type,
                "status": snapshot.status,
                "server_scope": asdict(snapshot.server_scope),
                "expected_rankings": list(snapshot.expected_rankings),
            },
            "coverage": asdict(cov),
            "readiness": asdict(readiness),
            "operational_truth": "READY" if readiness.operational_truth_ready else "NOT_READY",
        }
        report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self._store_report_path(snapshot.id, str(report_path))
        return str(report_path)

    def _store_report_path(self, snapshot_id: str, report_path: str) -> None:
        payload = self._load()
        for item in payload.get("snapshots", []) or []:
            if isinstance(item, dict) and str(item.get("id")) == snapshot_id:
                item["completion_report_file"] = report_path
                self._append_audit(item, "completion_report_written", detail=report_path)
                item["updated_at"] = self._now()
                break
        self._save(payload)

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
    def _load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _from_raw(raw: dict) -> ManagedSnapshot:
        server_scope = SnapshotService._server_scope_from_raw(raw)
        servers = SnapshotService._expand_server_scope(server_scope)
        rankings = SnapshotService._clean_rankings(raw.get("expected_rankings", []) or DEFAULT_EXPECTED_RANKINGS)
        status = SnapshotService._normalize_status(str(raw.get("status") or "open"))
        audit_entries = []
        for entry in raw.get("audit", []) or []:
            if isinstance(entry, dict):
                audit_entries.append(SnapshotAuditEntry(
                    event=str(entry.get("event") or "unknown"),
                    at=str(entry.get("at") or ""),
                    actor=str(entry.get("actor") or "sentinel"),
                    detail=str(entry.get("detail") or ""),
                ))
        return ManagedSnapshot(
            id=str(raw.get("id") or ""),
            name=str(raw.get("name") or "Unnamed Snapshot"),
            snapshot_type=str(raw.get("snapshot_type") or "screenshot_upload"),
            status=status,
            description=str(raw.get("description") or ""),
            expected_rankings=rankings,
            created_at=str(raw.get("created_at") or ""),
            updated_at=str(raw.get("updated_at") or ""),
            source=str(raw.get("source") or ""),
            assigned_servers=servers,
            server_scope=server_scope,
            locked=status in LOCKED_STATUSES,
            audit=audit_entries,
            completion_report_file=str(raw.get("completion_report_file") or ""),
        )

    @staticmethod
    def _snapshot_binding(snapshot: ManagedSnapshot) -> dict[str, Any]:
        return {
            "id": snapshot.id,
            "name": snapshot.name,
            "type": snapshot.snapshot_type,
            "status_at_import": snapshot.status,
            "description": snapshot.description,
            "expected_rankings": list(snapshot.expected_rankings),
            "expected_servers": list(snapshot.assigned_servers),
            "server_scope": asdict(snapshot.server_scope),
            "bound_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }

    @staticmethod
    def _server_scope_from_raw(raw: dict[str, Any]) -> ServerScope:
        scope_raw = raw.get("server_scope") if isinstance(raw.get("server_scope"), dict) else {}
        if scope_raw:
            mode = str(scope_raw.get("mode") or "selected").lower()
            start = SnapshotService._optional_int(scope_raw.get("start"))
            end = SnapshotService._optional_int(scope_raw.get("end"))
            servers = SnapshotService._clean_servers(scope_raw.get("servers", []) or [])
            return SnapshotService._normalize_server_scope(ServerScope(mode=mode, start=start, end=end, servers=servers))
        legacy_servers = SnapshotService._clean_servers(raw.get("assigned_servers", []) or [])
        return SnapshotService._normalize_server_scope(ServerScope(mode="selected", servers=legacy_servers))

    @staticmethod
    def _build_server_scope(*, mode: str, assigned_servers: list[Any] | str, server_range_start: int | str | None, server_range_end: int | str | None) -> ServerScope:
        clean_mode = str(mode or "selected").strip().lower()
        if clean_mode not in SERVER_SCOPE_MODES:
            clean_mode = "selected"
        if clean_mode == "all":
            return ServerScope(mode="all", servers=[])
        if clean_mode == "range":
            return SnapshotService._normalize_server_scope(ServerScope(mode="range", start=SnapshotService._optional_int(server_range_start), end=SnapshotService._optional_int(server_range_end)))
        return SnapshotService._normalize_server_scope(ServerScope(mode="selected", servers=SnapshotService._clean_servers(assigned_servers)))

    @staticmethod
    def _normalize_server_scope(scope: ServerScope) -> ServerScope:
        mode = scope.mode if scope.mode in SERVER_SCOPE_MODES else "selected"
        if mode == "range":
            start = scope.start
            end = scope.end
            if start and end:
                if start > end:
                    start, end = end, start
                return ServerScope(mode="range", start=start, end=end, servers=[])
            return ServerScope(mode="selected", servers=[])
        if mode == "all":
            return ServerScope(mode="all", servers=[])
        return ServerScope(mode="selected", servers=SnapshotService._clean_servers(scope.servers))

    @staticmethod
    def _expand_server_scope(scope: ServerScope) -> list[int]:
        if scope.mode == "range" and scope.start and scope.end:
            return list(range(scope.start, scope.end + 1))
        if scope.mode == "selected":
            return SnapshotService._clean_servers(scope.servers)
        return []

    def _expected_servers_for_snapshot(self, snapshot: ManagedSnapshot | None, report: dict[str, Any]) -> list[int]:
        if snapshot is None:
            return []
        if snapshot.server_scope.mode == "all":
            known = set(snapshot.assigned_servers)
            for item in report.get("imports") or []:
                if isinstance(item, dict):
                    server = self._optional_int(item.get("server"))
                    if server:
                        known.add(server)
            return sorted(known)
        return list(snapshot.assigned_servers)

    @staticmethod
    def _append_audit(item: dict[str, Any], event: str, before: dict[str, Any] | None = None, detail: str = "") -> None:
        audit = item.setdefault("audit", [])
        if not isinstance(audit, list):
            audit = []
            item["audit"] = audit
        entry: dict[str, Any] = {"event": event, "at": SnapshotService._now(), "actor": "sentinel", "detail": detail}
        if before:
            entry["before_status"] = before.get("status")
            entry["before_server_scope"] = before.get("server_scope")
            entry["before_assigned_servers"] = before.get("assigned_servers")
            entry["before_expected_rankings"] = before.get("expected_rankings")
        audit.append(entry)

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
            normalized = SnapshotService._clean_ranking(value)
            if normalized and normalized not in cleaned:
                cleaned.append(normalized)
        return cleaned or list(DEFAULT_EXPECTED_RANKINGS)

    @staticmethod
    def _clean_ranking(value: str) -> str:
        return str(value or "").strip().lower().replace(" ", "_")

    @staticmethod
    def _clean_servers(values: list[Any] | str) -> list[int]:
        raw_values: list[Any]
        if isinstance(values, str):
            raw_values = re.split(r"[^0-9]+", values)
        else:
            raw_values = list(values or [])
        servers: list[int] = []
        for value in raw_values:
            try:
                server = int(value)
            except (TypeError, ValueError):
                continue
            if server > 0 and server not in servers:
                servers.append(server)
        return sorted(servers)

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        parsed = SnapshotService._int(value)
        return parsed or None

    @staticmethod
    def _int(value: Any) -> int:
        try:
            if value is None:
                return 0
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _normalize_status(status: str) -> str:
        clean = str(status or "open").strip().lower()
        clean = STATUS_ALIASES.get(clean, clean)
        return clean if clean in LIFECYCLE_STATUSES else "open"

    @staticmethod
    def _slug_id(name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "snapshot"
        return f"{slug}-{uuid4().hex[:8]}"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
