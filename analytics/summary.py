from database.sqlite import Database


def print_collection_summary():
    db = Database()

    collections = db.list_collections()

    print("\n========== LastWarIntel Summary ==========\n")

    if not collections:
        print("Keine Collections gefunden.")
        return

    for collection in collections:
        collection_id = collection["id"]
        name = collection["name"]
        ctype = collection["type"]
        status = collection["status"]

        print(f"Collection: {name}")
        print(f"Type:       {ctype}")
        print(f"Status:     {status}")

        snapshot_count = db.execute(
            """
            SELECT COUNT(*) AS count
            FROM snapshots
            WHERE collection_id = ?
            """,
            (collection_id,),
        )[0]["count"]

        server_count = db.execute(
            """
            SELECT COUNT(DISTINCT server) AS count
            FROM snapshots
            WHERE collection_id = ?
            """,
            (collection_id,),
        )[0]["count"]

        ranking_count = db.execute(
            """
            SELECT COUNT(*) AS count
            FROM ranking_entries re
            JOIN snapshots s ON s.id = re.snapshot_id
            WHERE s.collection_id = ?
            """,
            (collection_id,),
        )[0]["count"]

        metric_count = db.execute(
            """
            SELECT COUNT(*) AS count
            FROM metrics m
            JOIN snapshots s ON s.id = m.snapshot_id
            WHERE s.collection_id = ?
            """,
            (collection_id,),
        )[0]["count"]

        city_count = db.execute(
            """
            SELECT COUNT(*) AS count
            FROM city_stats cs
            JOIN snapshots s ON s.id = cs.snapshot_id
            WHERE s.collection_id = ?
            """,
            (collection_id,),
        )[0]["count"]

        influence_count = db.execute(
            """
            SELECT COUNT(*) AS count
            FROM influence_points
            WHERE collection_id = ?
            """,
            (collection_id,),
        )[0]["count"]

        pact_count = db.execute(
            """
            SELECT COUNT(*) AS count
            FROM pact_entries
            WHERE collection_id = ?
            """,
            (collection_id,),
        )[0]["count"]

        print(f"Servers:    {server_count}")
        print(f"Snapshots:  {snapshot_count}")
        print(f"Rankings:   {ranking_count}")
        print(f"Metrics:    {metric_count}")
        print(f"Cities:     {city_count}")
        print(f"Influence:  {influence_count}")
        print(f"Pacts:      {pact_count}")

        ranking_types = db.execute(
            """
            SELECT rt.name, COUNT(*) AS count
            FROM ranking_entries re
            JOIN ranking_types rt ON rt.id = re.ranking_type_id
            JOIN snapshots s ON s.id = re.snapshot_id
            WHERE s.collection_id = ?
            GROUP BY rt.name
            ORDER BY rt.name
            """,
            (collection_id,),
        )

        if ranking_types:
            print("Ranking types:")
            for row in ranking_types:
                print(f"  - {row['name']}: {row['count']}")

        print("-" * 45)


if __name__ == "__main__":
    print_collection_summary()