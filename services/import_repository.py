"""Operational import repository for Sentinel runtime data.

The Command Center reads the latest import run from this repository instead of
benchmark or ground-truth artifacts.  The current implementation persists a
small JSON document; the boundary can later be backed by SQLite/PostgreSQL.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_IMPORT_REPORT = Path("data/latest_import_report.json")


class JsonImportRunRepository:
    def __init__(self, path: Path | str | None = None) -> None:
        self._path = Path(path or DEFAULT_IMPORT_REPORT)

    def load_latest_import(self) -> dict[str, Any] | None:
        if not self._path.exists():
            return None
        try:
            with self._path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def save_latest_import(self, payload: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def describe_source(self) -> str:
        return str(self._path)


def _int(value: Any) -> int:
    try:
        if value is None:
            return 0
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _status_for_group(rows: list[dict[str, Any]]) -> tuple[str, int, int]:
    if not rows:
        return "Incomplete", 0, 0
    conflicts = sum(1 for row in rows if row.get("data_guard_conflict") or "server_assignment_conflict" in str(row.get("server_warning") or ""))
    warnings = sum(1 for row in rows if row.get("server_warning") or row.get("rank_warning"))
    if conflicts:
        return "Review", conflicts, 85
    if warnings:
        return "Review", warnings, 90
    return "Ready", 0, 100


def build_import_run_report(
    grouped: dict[tuple[Any, str], list[dict[str, Any]]],
    *,
    screenshots: int,
    runtime_seconds: float,
    output_file: str,
) -> dict[str, Any]:
    server_imports: list[dict[str, Any]] = []
    review_items: list[dict[str, Any]] = []
    total_rows = 0
    servers: set[int] = set()

    for (server, ranking_type), rows in sorted(grouped.items(), key=lambda item: str(item[0])):
        rows = list(rows or [])
        total_rows += len(rows)
        if isinstance(server, int):
            servers.add(server)
        status, review_count, confidence = _status_for_group(rows)
        if ranking_type == "data_guard_quarantine":
            status = "Quarantine"
            review_count = len(rows)
            confidence = 0
        source_files = sorted({str(row.get("source_file")) for row in rows if row.get("source_file")})
        server_imports.append({
            "server": server if isinstance(server, int) else None,
            "ranking_type": ranking_type,
            "rows": len(rows),
            "status": status,
            "confidence": confidence,
            "review_count": review_count,
            "screenshots": len(source_files),
            "source_files": source_files,
            "source": f"{server}_{ranking_type}",
        })
        for row in rows:
            warning = str(row.get("server_warning") or "")
            if ranking_type == "data_guard_quarantine":
                review_items.append({
                    "server": _int(row.get("original_server")) or None,
                    "candidate_server": _int(row.get("candidate_server")) or None,
                    "ranking_type": str(row.get("ranking_type") or "unknown"),
                    "rank": _int(row.get("rank")) or _int(row.get("computed_rank")) or None,
                    "title": "Data Guard quarantine",
                    "description": warning or "Data Guard isolated this block instead of guessing a server assignment.",
                    "severity": "warning",
                    "action": "Review quarantined screenshot block",
                    "reason": "data_guard_quarantine",
                    "screenshot": row.get("source_file") or "",
                })
            elif row.get("data_guard_conflict") or "server_assignment_conflict" in warning:
                review_items.append({
                    "server": server if isinstance(server, int) else None,
                    "ranking_type": ranking_type,
                    "rank": _int(row.get("rank")) or _int(row.get("computed_rank")) or None,
                    "title": "Data Guard server assignment conflict",
                    "description": warning or "Server assignment evidence conflicted during import.",
                    "severity": "warning",
                    "action": "Review screenshot server assignment",
                    "reason": "server_assignment_conflict",
                    "screenshot": row.get("source_file") or "",
                })

    status = "Review" if review_items else "Ready"
    readiness = 100 if not review_items else max(50, int(round(100 - min(len(review_items) * 5, 50))))
    return {
        "schema": "sentinel.import_run.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "runtime_seconds": round(float(runtime_seconds), 2),
        "screenshots": int(screenshots),
        "output_file": output_file,
        "servers": sorted(servers),
        "server_count": len(servers),
        "rows": total_rows,
        "status": status,
        "readiness": readiness,
        "review_count": len(review_items),
        "data_guard": {
            "status": "Warning" if review_items else "Healthy",
            "warnings": len(review_items),
            "critical": 0,
            "checks": ["server_assignment", "data_quality_loop", "quarantine"],
        },
        "imports": server_imports,
        "reviews": review_items,
        "recent_operations": [
            {
                "time": "latest",
                "title": "Import completed",
                "detail": f"{screenshots} screenshots · {len(servers)} servers · {total_rows} rows · {runtime_seconds:.2f}s",
                "severity": "success" if not review_items else "warning",
            },
            {
                "time": "latest",
                "title": "Sentinel Data Guard completed",
                "detail": f"{len(review_items)} assignment review item(s) detected",
                "severity": "success" if not review_items else "warning",
            },
        ],
    }
