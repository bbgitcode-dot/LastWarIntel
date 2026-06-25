from pathlib import Path
import sqlite3
import uuid
from typing import Optional, Any


DB_PATH = Path("data/lastwarintel.sqlite")


class Database:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def create_collection(
        self,
        name: str,
        description: str = "",
        collection_type: str = "custom",
        expected_servers: Optional[int] = None,
    ) -> int:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO collections (
                    uuid, name, description, type, expected_servers
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    name,
                    description,
                    collection_type,
                    expected_servers,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def list_collections(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT *
                FROM collections
                ORDER BY created_at DESC
                """
            ).fetchall()

    def get_collection_by_name(self, name: str) -> Optional[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT *
                FROM collections
                WHERE name = ?
                """,
                (name,),
            ).fetchone()

    def create_snapshot(
        self,
        collection_id: int,
        server: int,
        status: str = "pending",
        parser_version: Optional[str] = None,
        ocr_engine: Optional[str] = None,
        ocr_version: Optional[str] = None,
    ) -> int:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO snapshots (
                    uuid,
                    collection_id,
                    server,
                    status,
                    parser_version,
                    ocr_engine,
                    ocr_version
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    collection_id,
                    server,
                    status,
                    parser_version,
                    ocr_engine,
                    ocr_version,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_latest_snapshot(
        self,
        collection_id: int,
        server: int,
    ) -> Optional[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT *
                FROM snapshots
                WHERE collection_id = ?
                  AND server = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (collection_id, server),
            ).fetchone()

    def update_snapshot_status(self, snapshot_id: int, status: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE snapshots
                SET status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, snapshot_id),
            )
            conn.commit()

    def get_or_create_ranking_type(
        self,
        name: str,
        description: str = "",
    ) -> int:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT id
                FROM ranking_types
                WHERE name = ?
                """,
                (name,),
            ).fetchone()

            if row:
                return row["id"]

            cursor = conn.execute(
                """
                INSERT INTO ranking_types (
                    name,
                    description
                )
                VALUES (?, ?)
                """,
                (name, description),
            )
            conn.commit()
            return cursor.lastrowid

    def get_or_create_entity(
        self,
        entity_type: str,
        name: str,
        tag: Optional[str] = None,
    ) -> int:
        clean_name = name.strip() if name else "UNKNOWN"
        clean_tag = tag.strip() if tag else None

        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT id
                FROM entities
                WHERE entity_type = ?
                  AND COALESCE(tag, '') = COALESCE(?, '')
                  AND name = ?
                """,
                (entity_type, clean_tag, clean_name),
            ).fetchone()

            if row:
                return row["id"]

            cursor = conn.execute(
                """
                INSERT INTO entities (
                    uuid,
                    entity_type,
                    tag,
                    name
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    entity_type,
                    clean_tag,
                    clean_name,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def insert_ranking_entry(
        self,
        snapshot_id: int,
        ranking_type_id: int,
        entity_id: int,
        rank: int,
        value: int,
        source_file: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> int:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT OR REPLACE INTO ranking_entries (
                    snapshot_id,
                    ranking_type_id,
                    entity_id,
                    rank,
                    value,
                    source_file,
                    confidence,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    snapshot_id,
                    ranking_type_id,
                    entity_id,
                    rank,
                    value,
                    source_file,
                    confidence,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def insert_screenshot(
        self,
        filename: str,
        file_path: str,
        sha256: str,
        snapshot_id: Optional[int] = None,
        screenshot_type: Optional[str] = None,
    ) -> int:
        with self.connect() as conn:
            existing = conn.execute(
                """
                SELECT id
                FROM screenshots
                WHERE sha256 = ?
                """,
                (sha256,),
            ).fetchone()

            if existing:
                return existing["id"]

            cursor = conn.execute(
                """
                INSERT INTO screenshots (
                    snapshot_id,
                    filename,
                    file_path,
                    sha256,
                    screenshot_type
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    filename,
                    file_path,
                    sha256,
                    screenshot_type,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def insert_ocr_result(
        self,
        screenshot_id: int,
        raw_json: str,
        ocr_engine: str,
        ocr_version: Optional[str] = None,
        parser_version: Optional[str] = None,
    ) -> int:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO ocr_results (
                    screenshot_id,
                    ocr_engine,
                    ocr_version,
                    parser_version,
                    raw_json
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    screenshot_id,
                    ocr_engine,
                    ocr_version,
                    parser_version,
                    raw_json,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_collection_summary(self, collection_id: int) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT
                    s.server,
                    rt.name AS ranking_type,
                    COUNT(re.id) AS entries
                FROM snapshots s
                LEFT JOIN ranking_entries re
                    ON re.snapshot_id = s.id
                LEFT JOIN ranking_types rt
                    ON rt.id = re.ranking_type_id
                WHERE s.collection_id = ?
                GROUP BY s.server, rt.name
                ORDER BY s.server, rt.name
                """,
                (collection_id,),
            ).fetchall()

    def fetch_ranking_entries(
        self,
        collection_id: int,
        ranking_type: str,
    ) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT
                    c.name AS collection,
                    s.server,
                    rt.name AS ranking_type,
                    re.rank,
                    e.entity_type,
                    e.tag,
                    e.name,
                    re.value,
                    re.source_file
                FROM ranking_entries re
                JOIN snapshots s
                    ON s.id = re.snapshot_id
                JOIN collections c
                    ON c.id = s.collection_id
                JOIN ranking_types rt
                    ON rt.id = re.ranking_type_id
                JOIN entities e
                    ON e.id = re.entity_id
                WHERE c.id = ?
                  AND rt.name = ?
                ORDER BY s.server, re.rank
                """,
                (collection_id, ranking_type),
            ).fetchall()

    def execute(
        self,
        query: str,
        params: tuple[Any, ...] = (),
    ) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(query, params).fetchall()