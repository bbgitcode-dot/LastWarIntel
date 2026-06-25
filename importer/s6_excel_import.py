from pathlib import Path
import argparse
import re
import time
from typing import Optional

import pandas as pd

from database.sqlite import Database


DEFAULT_FILE = Path("input/LastWarS6_pre-season.xlsx")


def parse_int(value) -> Optional[int]:
    if pd.isna(value):
        return None

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return int(value)

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
    text = re.sub(r"[^0-9-]", "", text)

    if not text or text == "-":
        return None

    return int(text) * multiplier


def parse_server(value) -> Optional[int]:
    number = parse_int(value)
    if number is None:
        return None

    if 1 <= number <= 9999:
        return number

    return None


def normalize_text(value) -> Optional[str]:
    if pd.isna(value):
        return None

    text = str(value).strip()
    return text if text else None


def get_or_create_collection(db: Database, name: str, description: str, collection_type: str) -> int:
    existing = db.get_collection_by_name(name)
    if existing:
        return existing["id"]

    return db.create_collection(
        name=name,
        description=description,
        collection_type=collection_type,
    )


def get_or_create_snapshot(db: Database, collection_id: int, server: int) -> int:
    existing = db.get_latest_snapshot(collection_id, server)
    if existing:
        return existing["id"]

    return db.create_snapshot(
        collection_id=collection_id,
        server=server,
        status="complete",
        parser_version="s6_excel_import_v2",
    )


def ensure_extra_tables(db: Database) -> None:
    with db.connect() as conn:
        conn.executescript(
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

            CREATE TABLE IF NOT EXISTS city_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                alliance TEXT NOT NULL,
                city_level_1 INTEGER,
                city_level_2 INTEGER,
                city_level_3 INTEGER,
                influence_points INTEGER,
                source_file TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (snapshot_id) REFERENCES snapshots(id),
                UNIQUE(snapshot_id, alliance)
            );

            CREATE TABLE IF NOT EXISTS influence_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_id INTEGER NOT NULL,
                server INTEGER,
                faction TEXT,
                alliance TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                value INTEGER,
                source_file TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (collection_id) REFERENCES collections(id)
            );

            CREATE TABLE IF NOT EXISTS pact_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_id INTEGER NOT NULL,
                server INTEGER,
                alliance TEXT NOT NULL,
                date_label TEXT,
                time_label TEXT,
                pact_with TEXT,
                source_file TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (collection_id) REFERENCES collections(id)
            );
            """
        )
        conn.commit()


def clear_collection_data(db: Database, collection_id: int) -> None:
    with db.connect() as conn:
        conn.executescript(
            f"""
            DELETE FROM ranking_entries
            WHERE snapshot_id IN (
                SELECT id FROM snapshots WHERE collection_id = {collection_id}
            );

            DELETE FROM metrics
            WHERE snapshot_id IN (
                SELECT id FROM snapshots WHERE collection_id = {collection_id}
            );

            DELETE FROM city_stats
            WHERE snapshot_id IN (
                SELECT id FROM snapshots WHERE collection_id = {collection_id}
            );

            DELETE FROM influence_points
            WHERE collection_id = {collection_id};

            DELETE FROM pact_entries
            WHERE collection_id = {collection_id};
            """
        )
        conn.commit()


def insert_metric(db: Database, snapshot_id: int, metric_name: str, value: int, source_file: str) -> None:
    with db.connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO metrics (
                snapshot_id, metric_name, value, source_file, updated_at
            )
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (snapshot_id, metric_name, value, source_file),
        )
        conn.commit()


def import_alliances(db: Database, excel_file: Path) -> int:
    collection_id = get_or_create_collection(
        db,
        "S6 Preseason Alliances",
        "S6 preseason alliance strength from Alliances sheet",
        "alliance_ranking",
    )
    clear_collection_data(db, collection_id)

    ranking_type_id = db.get_or_create_ranking_type("alliance_power", "Alliance Power ranking")

    df = pd.read_excel(excel_file, sheet_name="Alliances")
    df["Server_clean"] = df["Server"].apply(parse_server)
    df["Alliance_clean"] = df["Alliance"].apply(normalize_text)
    df["Strength_clean"] = df["Strength"].apply(parse_int)

    df = df.dropna(subset=["Server_clean", "Alliance_clean", "Strength_clean"])
    df = df.sort_values(["Server_clean", "Strength_clean"], ascending=[True, False])
    df["Rank_clean"] = df.groupby("Server_clean").cumcount() + 1

    count = 0

    for _, row in df.iterrows():
        server = int(row["Server_clean"])
        alliance = str(row["Alliance_clean"])
        strength = int(row["Strength_clean"])
        rank = int(row["Rank_clean"])

        snapshot_id = get_or_create_snapshot(db, collection_id, server)

        entity_id = db.get_or_create_entity(
            entity_type="alliance",
            tag=alliance,
            name=alliance,
        )

        db.insert_ranking_entry(
            snapshot_id=snapshot_id,
            ranking_type_id=ranking_type_id,
            entity_id=entity_id,
            rank=rank,
            value=strength,
            source_file=str(excel_file),
        )

        count += 1

    return count


def import_players(db: Database, excel_file: Path) -> int:
    collection_id = get_or_create_collection(
        db,
        "S6 Preseason THP",
        "S6 preseason total hero power from Players sheet",
        "total_hero_power",
    )
    clear_collection_data(db, collection_id)

    ranking_type_id = db.get_or_create_ranking_type("total_hero_power", "Total Hero Power ranking")

    df = pd.read_excel(excel_file, sheet_name="Players")
    df["Server_clean"] = df["Server"].apply(parse_server)
    df["Alliance_clean"] = df["Alliance"].apply(normalize_text)
    df["Player_clean"] = df["Player"].apply(normalize_text)
    df["THP_clean"] = df["THP"].apply(parse_int)

    df = df.dropna(subset=["Server_clean", "Player_clean", "THP_clean"])
    df = df.sort_values(["Server_clean", "THP_clean"], ascending=[True, False])
    df["Rank_clean"] = df.groupby("Server_clean").cumcount() + 1

    count = 0

    for _, row in df.iterrows():
        server = int(row["Server_clean"])
        alliance = normalize_text(row["Alliance_clean"])
        player = str(row["Player_clean"])
        thp = int(row["THP_clean"])
        rank = int(row["Rank_clean"])

        snapshot_id = get_or_create_snapshot(db, collection_id, server)

        entity_id = db.get_or_create_entity(
            entity_type="player",
            tag=alliance,
            name=player,
        )

        db.insert_ranking_entry(
            snapshot_id=snapshot_id,
            ranking_type_id=ranking_type_id,
            entity_id=entity_id,
            rank=rank,
            value=thp,
            source_file=str(excel_file),
        )

        count += 1

    return count


def import_overview_metrics(db: Database, excel_file: Path) -> int:
    collection_id = get_or_create_collection(
        db,
        "S6 Preseason Server Summary",
        "S6 preseason server summary from overview sheet",
        "server_summary",
    )
    clear_collection_data(db, collection_id)

    df = pd.read_excel(excel_file, sheet_name="overview", header=None)

    count = 0

    # Erste einfache Metrik: alle offensichtlichen Server/Strength-Paare in benachbarten Spalten finden.
    for col in range(df.shape[1] - 1):
        for row in range(df.shape[0]):
            server = parse_server(df.iloc[row, col])
            value = parse_int(df.iloc[row, col + 1])

            if server is None or value is None:
                continue

            if value < 1_000_000:
                continue

            snapshot_id = get_or_create_snapshot(db, collection_id, server)
            metric_name = f"overview_col_{col + 1}_value"

            insert_metric(
                db,
                snapshot_id,
                metric_name,
                value,
                str(excel_file),
            )
            count += 1

    return count


def import_cities(db: Database, excel_file: Path) -> int:
    collection_id = get_or_create_collection(
        db,
        "S6 Preseason Cities",
        "S6 preseason city and influence overview",
        "cities",
    )
    clear_collection_data(db, collection_id)

    df = pd.read_excel(excel_file, sheet_name="cities", header=None)

    server = None
    first_cell = normalize_text(df.iloc[0, 0])
    if first_cell:
        match = re.search(r"(\d{3,4})", first_cell)
        if match:
            server = int(match.group(1))

    if not server:
        return 0

    snapshot_id = get_or_create_snapshot(db, collection_id, server)

    count = 0

    for idx in range(1, len(df)):
        alliance = normalize_text(df.iloc[idx, 0])
        if not alliance:
            continue

        if alliance.lower() in {"alliance", "server"}:
            continue

        city_l1 = parse_int(df.iloc[idx, 1]) if df.shape[1] > 1 else None
        city_l2 = parse_int(df.iloc[idx, 2]) if df.shape[1] > 2 else None
        city_l3 = parse_int(df.iloc[idx, 3]) if df.shape[1] > 3 else None
        influence = parse_int(df.iloc[idx, 4]) if df.shape[1] > 4 else None

        if city_l1 is None and city_l2 is None and city_l3 is None and influence is None:
            continue

        with db.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO city_stats (
                    snapshot_id,
                    alliance,
                    city_level_1,
                    city_level_2,
                    city_level_3,
                    influence_points,
                    source_file,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    snapshot_id,
                    alliance,
                    city_l1,
                    city_l2,
                    city_l3,
                    influence,
                    str(excel_file),
                ),
            )
            conn.commit()

        count += 1

    return count


def import_influence_points(db: Database, excel_file: Path) -> int:
    collection_id = get_or_create_collection(
        db,
        "S6 Preseason Influence Points",
        "S6 influence point tracking from Influence points sheet",
        "influence_points",
    )
    clear_collection_data(db, collection_id)

    df = pd.read_excel(excel_file, sheet_name="Influence points")

    fixed_cols = {"#", "Faction", "Server ", "Server", "Alliance"}
    count = 0

    for _, row in df.iterrows():
        server = parse_server(row.get("Server ") if "Server " in row else row.get("Server"))
        faction = normalize_text(row.get("Faction"))
        alliance = normalize_text(row.get("Alliance"))

        if not alliance:
            continue

        for col in df.columns:
            if col in fixed_cols:
                continue

            value = parse_int(row.get(col))
            if value is None:
                continue

            with db.connect() as conn:
                conn.execute(
                    """
                    INSERT INTO influence_points (
                        collection_id,
                        server,
                        faction,
                        alliance,
                        metric_name,
                        value,
                        source_file
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        collection_id,
                        server,
                        faction,
                        alliance,
                        str(col),
                        value,
                        str(excel_file),
                    ),
                )
                conn.commit()

            count += 1

    return count


def import_pacts(db: Database, excel_file: Path) -> int:
    collection_id = get_or_create_collection(
        db,
        "S6 Preseason Pacts",
        "S6 pact timeline from pacts sheet",
        "pacts",
    )
    clear_collection_data(db, collection_id)

    df = pd.read_excel(excel_file, sheet_name="pacts", header=None)

    date_labels = list(df.iloc[0]) if len(df) > 0 else []
    time_labels = list(df.iloc[1]) if len(df) > 1 else []

    current_server = None
    count = 0

    for row_idx in range(1, len(df)):
        first = df.iloc[row_idx, 0]
        maybe_server = parse_server(first)

        if maybe_server:
            current_server = maybe_server
            continue

        alliance = normalize_text(first)
        if not current_server or not alliance:
            continue

        for col_idx in range(1, df.shape[1]):
            pact_with = normalize_text(df.iloc[row_idx, col_idx])
            if not pact_with:
                continue

            date_label = str(date_labels[col_idx]) if col_idx < len(date_labels) else ""
            time_label = str(time_labels[col_idx]) if col_idx < len(time_labels) else ""

            with db.connect() as conn:
                conn.execute(
                    """
                    INSERT INTO pact_entries (
                        collection_id,
                        server,
                        alliance,
                        date_label,
                        time_label,
                        pact_with,
                        source_file
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        collection_id,
                        current_server,
                        alliance,
                        date_label,
                        time_label,
                        pact_with,
                        str(excel_file),
                    ),
                )
                conn.commit()

            count += 1

    return count


def import_s6_excel(excel_file: Path) -> None:
    start = time.time()

    if not excel_file.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {excel_file}")

    db = Database()
    ensure_extra_tables(db)

    print(f"Importiere S6 Datei: {excel_file}")

    workbook = pd.ExcelFile(excel_file)
    sheets = workbook.sheet_names

    print("\nGefundene Blätter:")
    for sheet in sheets:
        print(f"  - {sheet}")

    results = {}

    if "overview" in sheets:
        print("\nImportiere overview...")
        results["overview_metrics"] = import_overview_metrics(db, excel_file)

    if "Alliances" in sheets:
        print("Importiere Alliances...")
        results["alliances"] = import_alliances(db, excel_file)

    if "Players" in sheets:
        print("Importiere Players...")
        results["players"] = import_players(db, excel_file)

    if "cities" in sheets:
        print("Importiere cities...")
        results["cities"] = import_cities(db, excel_file)

    if "Influence points" in sheets:
        print("Importiere Influence points...")
        results["influence_points"] = import_influence_points(db, excel_file)

    if "pacts" in sheets:
        print("Importiere pacts...")
        results["pacts"] = import_pacts(db, excel_file)

    duration = time.time() - start

    print("\n===== S6 IMPORT REPORT =====")
    for key, value in results.items():
        print(f"{key:20}: {value}")

    print(f"Dauer               : {duration:.2f} Sekunden")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Import S6 preseason Excel data into LastWarIntel."
    )
    parser.add_argument(
        "file",
        nargs="?",
        default=str(DEFAULT_FILE),
        help="Pfad zur S6 Excel-Datei",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    import_s6_excel(Path(args.file))