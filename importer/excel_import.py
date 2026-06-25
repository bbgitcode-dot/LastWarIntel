from pathlib import Path
import argparse
import re
import time
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from database.sqlite import Database


DEFAULT_FILE = Path("input/LastWarS5_post_Transfer.xlsx")


@dataclass
class ImportReport:
    collections_created: int = 0
    snapshots_created: int = 0
    entities_created: int = 0
    ranking_entries: int = 0
    metrics: int = 0
    skipped_rows: int = 0


def parse_power(value) -> Optional[int]:
    if pd.isna(value):
        return None

    text = str(value).strip().lower()
    text = text.replace(",", "").replace(" ", "")

    multiplier = 1
    if text.endswith("b"):
        multiplier = 1_000_000_000
        text = text[:-1]
    elif text.endswith("m"):
        multiplier = 1_000_000
        text = text[:-1]

    text = text.replace(".", "")
    text = re.sub(r"[^0-9]", "", text)

    if not text:
        return None

    return int(text) * multiplier


def parse_alliance(value):
    if pd.isna(value):
        return None, None

    text = str(value).strip()
    if not text:
        return None, None

    match = re.match(r"^\[?([A-Za-z0-9]+)\]?\s*(.*)$", text)

    if match:
        tag = match.group(1).strip()
        name = match.group(2).strip() or tag
        return tag, name

    return None, text


def ensure_metric_table(db: Database) -> None:
    with db.connect() as conn:
        conn.execute(
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
        conn.commit()


def insert_metric(
    db: Database,
    snapshot_id: int,
    metric_name: str,
    value: int,
    source_file: str,
) -> None:
    with db.connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO metrics (
                snapshot_id,
                metric_name,
                value,
                source_file,
                updated_at
            )
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (snapshot_id, metric_name, value, source_file),
        )
        conn.commit()


def get_or_create_collection(
    db: Database,
    name: str,
    description: str,
    collection_type: str,
) -> int:
    existing = db.get_collection_by_name(name)
    if existing:
        return existing["id"]

    return db.create_collection(
        name=name,
        description=description,
        collection_type=collection_type,
    )


def get_or_create_snapshot(
    db: Database,
    collection_id: int,
    server: int,
    parser_version: str = "excel_import_v2",
) -> tuple[int, bool]:
    existing = db.get_latest_snapshot(collection_id, server)

    if existing:
        return existing["id"], False

    snapshot_id = db.create_snapshot(
        collection_id=collection_id,
        server=server,
        status="complete",
        parser_version=parser_version,
    )

    return snapshot_id, True


def import_s4_summary(
    db: Database,
    excel_file: Path,
    report: ImportReport,
) -> None:
    sheet_name = "Tabelle2"
    print(f"\nImportiere S4 Summary aus Blatt: {sheet_name}")

    collection_id = get_or_create_collection(
        db=db,
        name="S4 Server Summary",
        description="Historical S4 aggregated server strength from Tabelle2",
        collection_type="historical_summary",
    )
    report.collections_created += 1

    df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)

    imported = 0

    for _, row in df.iterrows():
        server = row.iloc[5] if len(row) > 5 else None
        strength = row.iloc[8] if len(row) > 8 else None

        if pd.isna(server) or pd.isna(strength):
            report.skipped_rows += 1
            continue

        try:
            server = int(server)
        except Exception:
            report.skipped_rows += 1
            continue

        value = parse_power(strength)
        if not value:
            report.skipped_rows += 1
            continue

        snapshot_id, created = get_or_create_snapshot(db, collection_id, server)

        if created:
            report.snapshots_created += 1

        insert_metric(
            db=db,
            snapshot_id=snapshot_id,
            metric_name="server_strength_summary",
            value=value,
            source_file=str(excel_file),
        )

        imported += 1
        report.metrics += 1

        if imported % 25 == 0:
            print(f"  S4 Summary: {imported} Server importiert...")

    print(f"  Fertig: {imported} S4 Server-Summaries importiert.")


def import_alliance_sheet(
    db: Database,
    excel_file: Path,
    sheet_name: str,
    collection_name: str,
    report: ImportReport,
) -> None:
    print(f"\nImportiere Alliance Ranking aus Blatt: {sheet_name}")

    collection_id = get_or_create_collection(
        db=db,
        name=collection_name,
        description=f"Imported from Excel sheet {sheet_name}",
        collection_type="alliance_ranking",
    )
    report.collections_created += 1

    ranking_type_id = db.get_or_create_ranking_type(
        "alliance_power",
        "Alliance Power ranking",
    )

    df = pd.read_excel(excel_file, sheet_name=sheet_name)

    imported = 0

    for _, row in df.iterrows():
        server = row.get("Server")
        rank = row.get("#")
        alliance = row.get("Alliance")
        strength = row.get("Strength")

        if pd.isna(server) or pd.isna(rank) or pd.isna(alliance) or pd.isna(strength):
            report.skipped_rows += 1
            continue

        try:
            server = int(server)
            rank = int(rank)
        except Exception:
            report.skipped_rows += 1
            continue

        power = parse_power(strength)
        if not power:
            report.skipped_rows += 1
            continue

        tag, name = parse_alliance(alliance)
        if not name:
            report.skipped_rows += 1
            continue

        snapshot_id, created = get_or_create_snapshot(db, collection_id, server)

        if created:
            report.snapshots_created += 1

        entity_id = db.get_or_create_entity(
            entity_type="alliance",
            tag=tag,
            name=name,
        )

        db.insert_ranking_entry(
            snapshot_id=snapshot_id,
            ranking_type_id=ranking_type_id,
            entity_id=entity_id,
            rank=rank,
            value=power,
            source_file=str(excel_file),
        )

        imported += 1
        report.ranking_entries += 1

        if imported % 100 == 0:
            print(f"  {collection_name}: {imported} Einträge importiert...")

    print(f"  Fertig: {imported} Alliance-Einträge importiert.")


def list_workbook_sheets(excel_file: Path) -> list[str]:
    workbook = pd.ExcelFile(excel_file)
    return workbook.sheet_names


def import_excel(excel_file: Path) -> ImportReport:
    start = time.time()

    if not excel_file.exists():
        raise FileNotFoundError(f"Excel-Datei nicht gefunden: {excel_file}")

    db = Database()
    ensure_metric_table(db)

    report = ImportReport()

    print(f"Importiere Datei: {excel_file}")

    sheets = list_workbook_sheets(excel_file)

    print("\nGefundene Tabellenblätter:")
    for sheet in sheets:
        print(f"  - {sheet}")

    if "Tabelle2" in sheets:
        import_s4_summary(db, excel_file, report)

    if "preTransfer" in sheets:
        import_alliance_sheet(
            db=db,
            excel_file=excel_file,
            sheet_name="preTransfer",
            collection_name="S5 Pre Transfer",
            report=report,
        )

    if "postTransfer" in sheets:
        import_alliance_sheet(
            db=db,
            excel_file=excel_file,
            sheet_name="postTransfer",
            collection_name="S5 Post Transfer",
            report=report,
        )

    duration = time.time() - start

    print("\n===== IMPORT REPORT =====")
    print(f"Collections geprüft/erstellt: {report.collections_created}")
    print(f"Snapshots erstellt:          {report.snapshots_created}")
    print(f"Ranking Entries:             {report.ranking_entries}")
    print(f"Metrics:                     {report.metrics}")
    print(f"Übersprungene Zeilen:         {report.skipped_rows}")
    print(f"Dauer:                       {duration:.2f} Sekunden")

    return report


def parse_args():
    parser = argparse.ArgumentParser(
        description="Import LastWarIntel Excel data into SQLite."
    )

    parser.add_argument(
        "file",
        nargs="?",
        default=str(DEFAULT_FILE),
        help="Pfad zur Excel-Datei",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    import_excel(Path(args.file))