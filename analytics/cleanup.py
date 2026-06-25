from database.sqlite import Database


def delete_collection_by_name(name: str) -> None:
    db = Database()

    collection = db.get_collection_by_name(name)

    if not collection:
        print(f"Collection nicht gefunden: {name}")
        return

    collection_id = collection["id"]

    with db.connect() as conn:
        conn.execute(
            """
            DELETE FROM ranking_entries
            WHERE snapshot_id IN (
                SELECT id FROM snapshots WHERE collection_id = ?
            )
            """,
            (collection_id,),
        )

        conn.execute(
            """
            DELETE FROM metrics
            WHERE snapshot_id IN (
                SELECT id FROM snapshots WHERE collection_id = ?
            )
            """,
            (collection_id,),
        )

        conn.execute(
            """
            DELETE FROM city_stats
            WHERE snapshot_id IN (
                SELECT id FROM snapshots WHERE collection_id = ?
            )
            """,
            (collection_id,),
        )

        conn.execute(
            "DELETE FROM influence_points WHERE collection_id = ?",
            (collection_id,),
        )

        conn.execute(
            "DELETE FROM pact_entries WHERE collection_id = ?",
            (collection_id,),
        )

        conn.execute(
            "DELETE FROM snapshots WHERE collection_id = ?",
            (collection_id,),
        )

        conn.execute(
            "DELETE FROM collections WHERE id = ?",
            (collection_id,),
        )

        conn.commit()

    print(f"Collection gelöscht: {name}")


if __name__ == "__main__":
    delete_collection_by_name("Test Collection")