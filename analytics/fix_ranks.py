from database.sqlite import Database


def fix_alliance_ranks():
    db = Database()

    with db.connect() as conn:
        ranking_type = conn.execute(
            "SELECT id FROM ranking_types WHERE name = 'alliance_power'"
        ).fetchone()

        if not ranking_type:
            print("Ranking type alliance_power nicht gefunden.")
            return

        ranking_type_id = ranking_type["id"]

        snapshots = conn.execute(
            """
            SELECT DISTINCT snapshot_id
            FROM ranking_entries
            WHERE ranking_type_id = ?
            """,
            (ranking_type_id,),
        ).fetchall()

        fixed = 0

        for snapshot in snapshots:
            snapshot_id = snapshot["snapshot_id"]

            entries = conn.execute(
                """
                SELECT id, value
                FROM ranking_entries
                WHERE snapshot_id = ?
                  AND ranking_type_id = ?
                ORDER BY value DESC
                """,
                (snapshot_id, ranking_type_id),
            ).fetchall()

            # erst temporäre negative Ränge, damit UNIQUE-Konflikte vermieden werden
            for idx, entry in enumerate(entries, start=1):
                conn.execute(
                    "UPDATE ranking_entries SET rank = ? WHERE id = ?",
                    (-idx, entry["id"]),
                )

            for idx, entry in enumerate(entries, start=1):
                conn.execute(
                    """
                    UPDATE ranking_entries
                    SET rank = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (idx, entry["id"]),
                )

            fixed += len(entries)

        conn.commit()

    print(f"Alliance-Ranks neu berechnet: {fixed} Einträge")


if __name__ == "__main__":
    fix_alliance_ranks()