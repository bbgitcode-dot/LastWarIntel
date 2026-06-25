from pathlib import Path
import sqlite3


DB_PATH = Path("data/lastwarintel.sqlite")


def create_database(db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")

        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                description TEXT,
                type TEXT NOT NULL DEFAULT 'custom',
                status TEXT NOT NULL DEFAULT 'active',
                expected_servers INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT NOT NULL UNIQUE,
                collection_id INTEGER NOT NULL,
                server INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                parser_version TEXT,
                ocr_engine TEXT,
                ocr_version TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (collection_id) REFERENCES collections(id)
            );

            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT NOT NULL UNIQUE,
                entity_type TEXT NOT NULL,
                tag TEXT,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(entity_type, tag, name)
            );

            CREATE TABLE IF NOT EXISTS ranking_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS ranking_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                ranking_type_id INTEGER NOT NULL,
                entity_id INTEGER NOT NULL,
                rank INTEGER NOT NULL,
                value INTEGER NOT NULL,
                source_file TEXT,
                confidence REAL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (snapshot_id) REFERENCES snapshots(id),
                FOREIGN KEY (ranking_type_id) REFERENCES ranking_types(id),
                FOREIGN KEY (entity_id) REFERENCES entities(id),
                UNIQUE(snapshot_id, ranking_type_id, rank)
            );

            CREATE TABLE IF NOT EXISTS screenshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                sha256 TEXT NOT NULL UNIQUE,
                screenshot_type TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
            );

            CREATE TABLE IF NOT EXISTS ocr_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                screenshot_id INTEGER NOT NULL,
                ocr_engine TEXT NOT NULL,
                ocr_version TEXT,
                parser_version TEXT,
                raw_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (screenshot_id) REFERENCES screenshots(id)
            );

            CREATE INDEX IF NOT EXISTS idx_collections_name
                ON collections(name);

            CREATE INDEX IF NOT EXISTS idx_snapshots_collection_server
                ON snapshots(collection_id, server);

            CREATE INDEX IF NOT EXISTS idx_snapshots_server
                ON snapshots(server);

            CREATE INDEX IF NOT EXISTS idx_entities_type_name
                ON entities(entity_type, name);

            CREATE INDEX IF NOT EXISTS idx_entities_tag
                ON entities(tag);

            CREATE INDEX IF NOT EXISTS idx_ranking_entries_snapshot
                ON ranking_entries(snapshot_id);

            CREATE INDEX IF NOT EXISTS idx_ranking_entries_type_value
                ON ranking_entries(ranking_type_id, value);

            CREATE INDEX IF NOT EXISTS idx_screenshots_hash
                ON screenshots(sha256);
            """
        )

        seed_ranking_types(conn)
        conn.commit()


def seed_ranking_types(conn: sqlite3.Connection) -> None:
    default_types = [
        ("alliance_power", "Alliance Power ranking"),
        ("total_hero_power", "Total Hero Power ranking"),
    ]

    conn.executemany(
        """
        INSERT OR IGNORE INTO ranking_types (name, description)
        VALUES (?, ?);
        """,
        default_types,
    )


if __name__ == "__main__":
    create_database()
    print(f"Database created: {DB_PATH}")