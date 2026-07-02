"""Read-only Historical Import dashboard service.

Historical imports are reference coverage. They must not be mixed with
benchmark/ground-truth validation reports and they must not overwrite current
Operational Truth.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True, frozen=True)
class HistoricalCollectionView:
    collection: str
    source_file: str
    sheet: str
    ranking_type: str
    rows_imported: int
    rows_skipped: int
    servers: list[int]
    duration_seconds: float
    status: str
    message: str


@dataclass(slots=True, frozen=True)
class HistoricalSnapshotCoverage:
    collection: str
    collection_type: str
    source_file: str
    server_count: int
    row_count: int
    ranking_types: list[str]


@dataclass(slots=True, frozen=True)
class HistoricalImportDashboard:
    has_report: bool
    report_path: str
    status: str
    files_seen: list[str]
    rows_imported: int
    rows_skipped: int
    server_count: int
    servers: list[int]
    collection_count: int
    duration_seconds: float
    interrupted: bool
    error: str | None
    collections: list[HistoricalCollectionView] = field(default_factory=list)
    snapshot_coverage: list[HistoricalSnapshotCoverage] = field(default_factory=list)


class HistoricalImportService:
    """Build the Historical Import dashboard from report JSON + SQLite."""

    def __init__(self, report_path: Path | None = None, database_path: Path | None = None) -> None:
        self.report_path = report_path or Path("data/historical_import_report.json")
        self.database_path = database_path or Path("data/lastwarintel.sqlite")

    def get_dashboard(self) -> HistoricalImportDashboard:
        report = self._load_report()
        collections = self._collections_from_report(report)
        servers = sorted({server for item in collections for server in item.servers})
        snapshot_coverage = self._load_snapshot_coverage()
        if snapshot_coverage:
            servers_from_db = self._load_servers_from_db()
            servers = sorted(set(servers).union(servers_from_db))
        return HistoricalImportDashboard(
            has_report=bool(report),
            report_path=str(self.report_path),
            status=str(report.get("status", "Pending") if report else "Pending"),
            files_seen=[str(value) for value in report.get("files_seen", [])] if report else [],
            rows_imported=int(report.get("rows_imported", 0) or 0) if report else 0,
            rows_skipped=int(report.get("rows_skipped", 0) or 0) if report else 0,
            server_count=len(servers),
            servers=servers,
            collection_count=len(collections),
            duration_seconds=float(report.get("duration_seconds", 0.0) or 0.0) if report else 0.0,
            interrupted=bool(report.get("interrupted", False)) if report else False,
            error=report.get("error") if report else None,
            collections=collections,
            snapshot_coverage=snapshot_coverage,
        )

    def _load_report(self) -> dict:
        if not self.report_path.exists():
            return {}
        try:
            payload = json.loads(self.report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _collections_from_report(report: dict) -> list[HistoricalCollectionView]:
        rows: list[HistoricalCollectionView] = []
        for raw in report.get("collections", []) if report else []:
            if not isinstance(raw, dict):
                continue
            servers = []
            for server in raw.get("servers", []) or []:
                try:
                    servers.append(int(server))
                except (TypeError, ValueError):
                    continue
            rows.append(
                HistoricalCollectionView(
                    collection=str(raw.get("collection", "")),
                    source_file=str(raw.get("source_file", "")),
                    sheet=str(raw.get("sheet", "")),
                    ranking_type=str(raw.get("ranking_type", "")),
                    rows_imported=int(raw.get("rows_imported", 0) or 0),
                    rows_skipped=int(raw.get("rows_skipped", 0) or 0),
                    servers=sorted(set(servers)),
                    duration_seconds=float(raw.get("duration_seconds", 0.0) or 0.0),
                    status=str(raw.get("status", "")),
                    message=str(raw.get("message", "")),
                )
            )
        return rows

    def _load_servers_from_db(self) -> list[int]:
        if not self.database_path.exists() or self.database_path.stat().st_size == 0:
            return []
        try:
            with sqlite3.connect(self.database_path) as conn:
                rows = conn.execute(
                    """
                    SELECT DISTINCT s.server
                    FROM snapshots s
                    JOIN collections c ON c.id = s.collection_id
                    WHERE c.type LIKE 'historical_%'
                    ORDER BY s.server
                    """
                ).fetchall()
        except (OSError, sqlite3.DatabaseError):
            return []
        return [int(row[0]) for row in rows if row and row[0] is not None]

    def _load_snapshot_coverage(self) -> list[HistoricalSnapshotCoverage]:
        if not self.database_path.exists() or self.database_path.stat().st_size == 0:
            return []
        try:
            with sqlite3.connect(self.database_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT
                        c.name AS collection,
                        c.type AS collection_type,
                        COALESCE(MIN(re.source_file), '') AS source_file,
                        COUNT(DISTINCT s.server) AS server_count,
                        COUNT(re.id) AS row_count,
                        GROUP_CONCAT(DISTINCT rt.name) AS ranking_types
                    FROM collections c
                    JOIN snapshots s ON s.collection_id = c.id
                    JOIN ranking_entries re ON re.snapshot_id = s.id
                    JOIN ranking_types rt ON rt.id = re.ranking_type_id
                    WHERE c.type LIKE 'historical_%'
                    GROUP BY c.id, c.name, c.type
                    ORDER BY c.name
                    """
                ).fetchall()
        except (OSError, sqlite3.DatabaseError):
            return []
        coverage: list[HistoricalSnapshotCoverage] = []
        for row in rows:
            types = sorted({item.strip() for item in str(row["ranking_types"] or "").split(",") if item.strip()})
            coverage.append(
                HistoricalSnapshotCoverage(
                    collection=str(row["collection"]),
                    collection_type=str(row["collection_type"]),
                    source_file=str(row["source_file"]),
                    server_count=int(row["server_count"] or 0),
                    row_count=int(row["row_count"] or 0),
                    ranking_types=types,
                )
            )
        return coverage
