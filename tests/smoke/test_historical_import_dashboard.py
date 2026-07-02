from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from application.historical_import.service import HistoricalImportService


def test_historical_import_dashboard_reads_report(tmp_path: Path) -> None:
    report = tmp_path / "historical_import_report.json"
    report.write_text(
        json.dumps(
            {
                "status": "Ready",
                "files_seen": ["LastWarS5_post_Transfer.xlsx"],
                "rows_imported": 10,
                "rows_skipped": 2,
                "duration_seconds": 1.25,
                "collections": [
                    {
                        "collection": "S5 preTransfer",
                        "source_file": "LastWarS5_post_Transfer.xlsx",
                        "sheet": "preTransfer",
                        "ranking_type": "alliance_power",
                        "rows_imported": 10,
                        "rows_skipped": 2,
                        "servers": [549, "550", "bad"],
                        "duration_seconds": 0.1,
                        "status": "Ready",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    db = tmp_path / "empty.sqlite"
    dashboard = HistoricalImportService(report_path=report, database_path=db).get_dashboard()

    assert dashboard.has_report is True
    assert dashboard.status == "Ready"
    assert dashboard.rows_imported == 10
    assert dashboard.rows_skipped == 2
    assert dashboard.server_count == 2
    assert dashboard.servers == [549, 550]
    assert dashboard.collections[0].ranking_type == "alliance_power"


def test_historical_import_dashboard_reads_sqlite_coverage(tmp_path: Path) -> None:
    report = tmp_path / "historical_import_report.json"
    report.write_text(json.dumps({"status": "Ready", "collections": []}), encoding="utf-8")
    db = tmp_path / "lastwarintel.sqlite"
    with sqlite3.connect(db) as conn:
        conn.executescript(
            """
            CREATE TABLE collections (id INTEGER PRIMARY KEY, name TEXT, type TEXT);
            CREATE TABLE snapshots (id INTEGER PRIMARY KEY, collection_id INTEGER, server INTEGER);
            CREATE TABLE ranking_types (id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE ranking_entries (id INTEGER PRIMARY KEY, snapshot_id INTEGER, ranking_type_id INTEGER, source_file TEXT);
            INSERT INTO collections VALUES (1, 'S6 Pre Season', 'historical_s6');
            INSERT INTO snapshots VALUES (1, 1, 554);
            INSERT INTO ranking_types VALUES (1, 'alliance_power');
            INSERT INTO ranking_entries VALUES (1, 1, 1, 'LastWarS6_pre-season.xlsx');
            """
        )
    dashboard = HistoricalImportService(report_path=report, database_path=db).get_dashboard()

    assert dashboard.server_count == 1
    assert dashboard.snapshot_coverage[0].collection == "S6 Pre Season"
    assert dashboard.snapshot_coverage[0].server_count == 1
    assert dashboard.snapshot_coverage[0].ranking_types == ["alliance_power"]
