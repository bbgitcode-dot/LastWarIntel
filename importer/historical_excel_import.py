"""Import Sentinel historical Excel workbooks into SQLite.

This importer is intentionally scoped as a historical/reference loader. It does
not write Operational Truth and it does not touch the latest OCR import report.
The Command Center can use the resulting SQLite collections as a broader server
coverage baseline while current-run reviews remain authoritative blockers.

v0.9.5.69 hardens the importer for large historical workbooks:
- one SQLite transaction per sheet instead of per-row commits
- cached collection/snapshot/entity/ranking-type lookups
- explicit progress output via --verbose
- bounded, relevant sheet processing only
- partial reports on interruption/failure
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.schema import create_database
from database.sqlite import Database

DEFAULT_INPUT_DIR = Path("input")
DEFAULT_REPORT_PATH = Path("data/historical_import_report.json")
S5_FILE = "LastWarS5_post_Transfer.xlsx"
S6_FILE = "LastWarS6_pre-season.xlsx"
PARSER_VERSION = "historical_excel_import_v2"


@dataclass
class HistoricalImportCollectionReport:
    collection: str
    source_file: str
    sheet: str
    ranking_type: str
    rows_imported: int = 0
    rows_skipped: int = 0
    servers: list[int] = field(default_factory=list)
    duration_seconds: float = 0.0
    status: str = "Ready"
    message: str = ""


@dataclass
class HistoricalImportReport:
    schema: str = "sentinel.historical_import_report.v2"
    status: str = "Ready"
    files_seen: list[str] = field(default_factory=list)
    collections: list[HistoricalImportCollectionReport] = field(default_factory=list)
    rows_imported: int = 0
    rows_skipped: int = 0
    servers: list[int] = field(default_factory=list)
    duration_seconds: float = 0.0
    interrupted: bool = False
    error: str | None = None

    def add_collection(self, collection: HistoricalImportCollectionReport) -> None:
        self.collections.append(collection)
        self.rows_imported += collection.rows_imported
        self.rows_skipped += collection.rows_skipped
        self.servers = sorted(set(self.servers).union(collection.servers))


@dataclass(frozen=True)
class SheetSpec:
    source_file: str
    sheet: str
    collection_name: str
    collection_type: str
    ranking_type: str
    entity_type: str
    server_column: str = "Server"
    rank_column: str = "#"
    alliance_column: str = "Alliance"
    value_column: str = "Strength"
    player_column: str | None = None
    description: str = ""


def log(verbose: bool, message: str) -> None:
    if verbose:
        print(message, flush=True)


def parse_int(value: Any) -> int | None:
    if pd.isna(value):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    text = str(value).strip().lower()
    if not text:
        return None
    multiplier = 1
    if text.endswith("b"):
        multiplier = 1_000_000_000
        text = text[:-1]
    elif text.endswith("m"):
        multiplier = 1_000_000
        text = text[:-1]
    text = text.replace(",", "").replace(".", "").replace(" ", "")
    text = re.sub(r"[^0-9-]", "", text)
    if not text or text == "-":
        return None
    try:
        return int(text) * multiplier
    except ValueError:
        return None


def parse_server(value: Any) -> int | None:
    number = parse_int(value)
    if number is None:
        return None
    if 1 <= number <= 9999:
        return number
    return None


def normalize_text(value: Any) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def parse_alliance_text(value: Any) -> tuple[str | None, str | None]:
    text = normalize_text(value)
    if not text:
        return None, None
    match = re.match(r"^\[?([A-Za-z0-9]+)\]?\s*(.*)$", text)
    if match:
        tag = match.group(1).strip() or None
        name = match.group(2).strip() or tag
        return tag, name
    return None, text


class HistoricalBulkWriter:
    """Small cached SQLite writer for historical import batches."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn: sqlite3.Connection | None = None
        self.collections: dict[str, int] = {}
        self.ranking_types: dict[str, int] = {}
        self.entities: dict[tuple[str, str, str], int] = {}
        self.snapshots: dict[tuple[int, int], int] = {}

    def __enter__(self) -> "HistoricalBulkWriter":
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.conn.execute("PRAGMA journal_mode = WAL;")
        self.conn.execute("PRAGMA synchronous = NORMAL;")
        self.conn.execute("PRAGMA temp_store = MEMORY;")
        self._load_caches()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        if self.conn is None:
            return
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.conn.close()
        self.conn = None

    @property
    def c(self) -> sqlite3.Connection:
        if self.conn is None:
            raise RuntimeError("HistoricalBulkWriter is not open")
        return self.conn

    def _load_caches(self) -> None:
        for row in self.c.execute("SELECT id, name FROM collections"):
            self.collections[str(row["name"])] = int(row["id"])
        for row in self.c.execute("SELECT id, name FROM ranking_types"):
            self.ranking_types[str(row["name"])] = int(row["id"])
        for row in self.c.execute("SELECT id, entity_type, tag, name FROM entities"):
            key = (str(row["entity_type"]), str(row["tag"] or ""), str(row["name"]))
            self.entities[key] = int(row["id"])
        for row in self.c.execute("SELECT id, collection_id, server FROM snapshots"):
            self.snapshots[(int(row["collection_id"]), int(row["server"]))] = int(row["id"])

    def ensure_collection(self, *, name: str, description: str, collection_type: str) -> int:
        if name in self.collections:
            return self.collections[name]
        cursor = self.c.execute(
            """
            INSERT INTO collections (uuid, name, description, type, expected_servers)
            VALUES (?, ?, ?, ?, NULL)
            """,
            (str(uuid.uuid4()), name, description, collection_type),
        )
        cid = int(cursor.lastrowid)
        self.collections[name] = cid
        return cid

    def ensure_ranking_type(self, name: str, description: str = "") -> int:
        if name in self.ranking_types:
            return self.ranking_types[name]
        cursor = self.c.execute(
            "INSERT OR IGNORE INTO ranking_types (name, description) VALUES (?, ?)",
            (name, description),
        )
        if cursor.lastrowid:
            rid = int(cursor.lastrowid)
        else:
            row = self.c.execute("SELECT id FROM ranking_types WHERE name = ?", (name,)).fetchone()
            rid = int(row["id"])
        self.ranking_types[name] = rid
        return rid

    def ensure_snapshot(self, *, collection_id: int, server: int, parser_version: str) -> int:
        key = (collection_id, server)
        if key in self.snapshots:
            return self.snapshots[key]
        cursor = self.c.execute(
            """
            INSERT INTO snapshots (uuid, collection_id, server, status, parser_version, ocr_engine, ocr_version)
            VALUES (?, ?, ?, 'complete', ?, NULL, NULL)
            """,
            (str(uuid.uuid4()), collection_id, server, parser_version),
        )
        sid = int(cursor.lastrowid)
        self.snapshots[key] = sid
        return sid

    def ensure_entity(self, *, entity_type: str, name: str, tag: str | None = None) -> int:
        clean_name = name.strip() if name else "UNKNOWN"
        clean_tag = str(tag).strip() if tag is not None and str(tag).strip() else ""
        key = (entity_type, clean_tag, clean_name)
        if key in self.entities:
            return self.entities[key]
        cursor = self.c.execute(
            """
            INSERT OR IGNORE INTO entities (uuid, entity_type, tag, name)
            VALUES (?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), entity_type, clean_tag or None, clean_name),
        )
        if cursor.lastrowid:
            eid = int(cursor.lastrowid)
        else:
            row = self.c.execute(
                """
                SELECT id FROM entities
                WHERE entity_type = ? AND COALESCE(tag, '') = COALESCE(?, '') AND name = ?
                """,
                (entity_type, clean_tag or None, clean_name),
            ).fetchone()
            eid = int(row["id"])
        self.entities[key] = eid
        return eid

    def insert_ranking_entry(
        self,
        *,
        snapshot_id: int,
        ranking_type_id: int,
        entity_id: int,
        rank: int,
        value: int,
        source_file: str,
        confidence: float,
    ) -> None:
        self.c.execute(
            """
            INSERT OR REPLACE INTO ranking_entries (
                snapshot_id, ranking_type_id, entity_id, rank, value, source_file, confidence, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (snapshot_id, ranking_type_id, entity_id, rank, value, source_file, confidence),
        )

    def ensure_metric_table(self) -> None:
        self.c.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                metric_name TEXT NOT NULL,
                value INTEGER NOT NULL,
                source_file TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (snapshot_id) REFERENCES snapshots(id),
                UNIQUE(snapshot_id, metric_name)
            );
            """
        )

    def insert_metric(self, *, snapshot_id: int, metric_name: str, value: int, source_file: str) -> None:
        self.c.execute(
            """
            INSERT OR REPLACE INTO metrics (snapshot_id, metric_name, value, source_file, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (snapshot_id, metric_name, value, source_file),
        )


def _load_sheet(excel_file: Path, sheet: str, *, header: int | None = 0) -> pd.DataFrame | None:
    workbook = pd.ExcelFile(excel_file)
    if sheet not in workbook.sheet_names:
        return None
    return pd.read_excel(excel_file, sheet_name=sheet, header=header)


def _prepare_dataframe(df: pd.DataFrame, spec: SheetSpec) -> pd.DataFrame:
    rename_map: dict[str, str] = {}
    if "Allianz" in df.columns and "Alliance" not in df.columns:
        rename_map["Allianz"] = "Alliance"
    if "THP" in df.columns and spec.value_column not in df.columns:
        rename_map["THP"] = spec.value_column
    if rename_map:
        df = df.rename(columns=rename_map)

    value_col = spec.value_column
    if value_col not in df.columns and value_col == "Strength" and "THP" in df.columns:
        value_col = "THP"

    required = [spec.server_column, value_col]
    if spec.rank_column != "__computed__":
        required.append(spec.rank_column)
    if spec.entity_type == "player":
        required.append(spec.player_column or "Player")
    else:
        required.append(spec.alliance_column)
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing column(s) {missing} in sheet {spec.sheet}")

    df = df.copy()
    df["__server_clean__"] = df[spec.server_column].apply(parse_server)
    df["__value_clean__"] = df[value_col].apply(parse_int)
    if spec.rank_column == "__computed__":
        df = df.dropna(subset=["__server_clean__", "__value_clean__"])
        df = df.sort_values(["__server_clean__", "__value_clean__"], ascending=[True, False])
        df["__rank_clean__"] = df.groupby("__server_clean__").cumcount() + 1
    else:
        df["__rank_clean__"] = df[spec.rank_column].apply(parse_int)
    return df


def import_ranking_sheet(
    writer: HistoricalBulkWriter,
    excel_file: Path,
    spec: SheetSpec,
    *,
    verbose: bool = False,
) -> HistoricalImportCollectionReport:
    started = time.time()
    collection = HistoricalImportCollectionReport(
        collection=spec.collection_name,
        source_file=str(excel_file),
        sheet=spec.sheet,
        ranking_type=spec.ranking_type,
    )
    if not excel_file.exists():
        collection.status = "Skipped"
        collection.message = "source file missing"
        return collection

    log(verbose, f"[historical-import] Sheet start: {excel_file.name} :: {spec.sheet}")
    try:
        df_raw = _load_sheet(excel_file, spec.sheet)
        if df_raw is None:
            collection.status = "Skipped"
            collection.message = "sheet missing"
            return collection
        df = _prepare_dataframe(df_raw, spec)
    except Exception as exc:
        collection.status = "Error"
        collection.message = str(exc)
        collection.duration_seconds = round(time.time() - started, 2)
        return collection

    collection_id = writer.ensure_collection(
        name=spec.collection_name,
        description=spec.description or f"Historical import from {excel_file.name}:{spec.sheet}",
        collection_type=spec.collection_type,
    )
    ranking_type_id = writer.ensure_ranking_type(spec.ranking_type, spec.ranking_type.replace("_", " ").title())

    seen_servers: set[int] = set()
    source = f"{excel_file}:{spec.sheet}"
    total = len(df)
    for idx, row in df.iterrows():
        server = parse_server(row.get("__server_clean__"))
        rank = parse_int(row.get("__rank_clean__"))
        value = parse_int(row.get("__value_clean__"))
        if server is None or rank is None or value is None:
            collection.rows_skipped += 1
            continue
        if spec.entity_type == "player":
            name = normalize_text(row.get(spec.player_column or "Player"))
            tag = normalize_text(row.get(spec.alliance_column))
        else:
            tag, name = parse_alliance_text(row.get(spec.alliance_column))
        if not name:
            collection.rows_skipped += 1
            continue
        snapshot_id = writer.ensure_snapshot(collection_id=collection_id, server=server, parser_version=PARSER_VERSION)
        entity_id = writer.ensure_entity(entity_type=spec.entity_type, tag=tag, name=name)
        writer.insert_ranking_entry(
            snapshot_id=snapshot_id,
            ranking_type_id=ranking_type_id,
            entity_id=entity_id,
            rank=rank,
            value=value,
            source_file=source,
            confidence=1.0,
        )
        collection.rows_imported += 1
        seen_servers.add(server)
        if verbose and collection.rows_imported % 250 == 0:
            print(f"  {collection.rows_imported} rows imported from {spec.sheet}...", flush=True)

    collection.servers = sorted(seen_servers)
    collection.duration_seconds = round(time.time() - started, 2)
    log(
        verbose,
        f"[historical-import] Sheet done: {spec.sheet} · imported={collection.rows_imported} skipped={collection.rows_skipped} servers={len(collection.servers)} duration={collection.duration_seconds}s",
    )
    return collection


def import_server_summary(
    writer: HistoricalBulkWriter,
    excel_file: Path,
    *,
    verbose: bool = False,
) -> HistoricalImportCollectionReport:
    started = time.time()
    spec_name = "S5 Post Transfer Server Strength Summary"
    report = HistoricalImportCollectionReport(
        collection=spec_name,
        source_file=str(excel_file),
        sheet="Tabelle2",
        ranking_type="server_strength_summary",
    )
    if not excel_file.exists():
        report.status = "Skipped"
        report.message = "source file missing"
        return report
    log(verbose, f"[historical-import] Summary start: {excel_file.name} :: Tabelle2")
    df = _load_sheet(excel_file, "Tabelle2", header=None)
    if df is None:
        report.status = "Skipped"
        report.message = "sheet missing"
        return report
    collection_id = writer.ensure_collection(
        name=spec_name,
        description="Historical S5 post-transfer total server strength, column F server and column I top-10 alliance strength.",
        collection_type="historical_server_summary",
    )
    writer.ensure_metric_table()
    seen_servers: set[int] = set()
    for _, row in df.iterrows():
        server = parse_server(row.iloc[5] if len(row) > 5 else None)
        strength = parse_int(row.iloc[8] if len(row) > 8 else None)
        if server is None or strength is None:
            report.rows_skipped += 1
            continue
        snapshot_id = writer.ensure_snapshot(collection_id=collection_id, server=server, parser_version=PARSER_VERSION)
        writer.insert_metric(
            snapshot_id=snapshot_id,
            metric_name="server_strength_top10_alliances",
            value=strength,
            source_file=f"{excel_file}:Tabelle2",
        )
        report.rows_imported += 1
        seen_servers.add(server)
    report.servers = sorted(seen_servers)
    report.duration_seconds = round(time.time() - started, 2)
    log(verbose, f"[historical-import] Summary done: imported={report.rows_imported} skipped={report.rows_skipped} servers={len(report.servers)} duration={report.duration_seconds}s")
    return report


def default_sheet_specs() -> list[SheetSpec]:
    return [
        SheetSpec(S5_FILE, "preTransfer", "S5 Pre Transfer Alliance Power", "historical_alliance_power", "alliance_power", "alliance", description="Top 10 alliances across 128 servers before the S5 transfer phase."),
        SheetSpec(S5_FILE, "postTransfer", "S5 Post Transfer Alliance Power", "historical_alliance_power", "alliance_power", "alliance", description="Top 10 alliances across 128 servers after the S5 transfer phase."),
        SheetSpec(S5_FILE, "pre gold vein alliance", "S5 Pre Gold Vein Alliance Power", "historical_alliance_power", "alliance_power", "alliance", alliance_column="Alliance", description="Top 10 alliances across 8 servers before Gold Vein."),
        SheetSpec(S5_FILE, "pre gold vein THP", "S5 Post Gold Vein Total Hero Power", "historical_total_hero_power", "total_hero_power", "player", player_column="Player", description="Top 10 THP across 8 servers after Gold Vein."),
        SheetSpec(S6_FILE, "Alliances", "S6 Preseason Alliance Power", "historical_alliance_power", "alliance_power", "alliance", rank_column="__computed__", description="Top 10 alliances across 8 servers before S6."),
        SheetSpec(S6_FILE, "Players", "S6 Preseason Total Hero Power", "historical_total_hero_power", "total_hero_power", "player", rank_column="__computed__", value_column="THP", player_column="Player", description="Top 10 THP across 8 servers before S6."),
    ]


def write_report(report: HistoricalImportReport, report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")


def import_historical_excels(
    input_dir: Path = DEFAULT_INPUT_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
    *,
    verbose: bool = False,
) -> HistoricalImportReport:
    start = time.time()
    create_database()
    db = Database()
    aggregate = HistoricalImportReport()

    s5_path = input_dir / S5_FILE
    s6_path = input_dir / S6_FILE
    for candidate in (s5_path, s6_path):
        if candidate.exists():
            aggregate.files_seen.append(str(candidate))
    log(verbose, f"[historical-import] Files seen: {len(aggregate.files_seen)}")

    try:
        with HistoricalBulkWriter(db.db_path) as writer:
            if s5_path.exists():
                aggregate.add_collection(import_server_summary(writer, s5_path, verbose=verbose))
            for spec in default_sheet_specs():
                excel_file = input_dir / spec.source_file
                if not excel_file.exists():
                    continue
                aggregate.add_collection(import_ranking_sheet(writer, excel_file, spec, verbose=verbose))
    except KeyboardInterrupt:
        aggregate.status = "Interrupted"
        aggregate.interrupted = True
        aggregate.error = "Interrupted by user"
        raise
    except Exception as exc:
        aggregate.status = "Error"
        aggregate.error = str(exc)
        raise
    finally:
        aggregate.duration_seconds = round(time.time() - start, 2)
        write_report(aggregate, report_path)

    aggregate.duration_seconds = round(time.time() - start, 2)
    write_report(aggregate, report_path)
    return aggregate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import historical Last War Excel workbooks into SQLite.")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR), help="Directory containing historical Excel workbooks.")
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH), help="JSON report path.")
    parser.add_argument("--verbose", action="store_true", help="Print progress for each workbook and sheet.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        report = import_historical_excels(Path(args.input_dir), Path(args.report), verbose=args.verbose)
    except KeyboardInterrupt:
        print("\nHistorical import interrupted. Partial report written if possible.", file=sys.stderr)
        raise SystemExit(130)
    print("===== HISTORICAL IMPORT REPORT =====")
    print(f"Files seen:      {len(report.files_seen)}")
    print(f"Servers:         {len(report.servers)}")
    print(f"Rows imported:   {report.rows_imported}")
    print(f"Rows skipped:    {report.rows_skipped}")
    print(f"Duration:        {report.duration_seconds}s")
    print(f"Report:          {args.report}")
