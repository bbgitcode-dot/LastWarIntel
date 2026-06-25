from database.sqlite import Database


class ServerRepository:
    def __init__(self):
        self.db = Database()

    # ------------------------------------------------------------------
    # Collections / Snapshots
    # ------------------------------------------------------------------

    def get_servers_with_collection(self, collection_name: str):
        return self.db.execute(
            """
            SELECT DISTINCT s.server
            FROM snapshots s
            JOIN collections c
                ON c.id = s.collection_id
            WHERE c.name = ?
            ORDER BY s.server
            """,
            (collection_name,),
        )

    def has_collection(self, server: int, collection_name: str) -> bool:
        rows = self.db.execute(
            """
            SELECT 1
            FROM snapshots s
            JOIN collections c
                ON c.id = s.collection_id
            WHERE s.server = ?
              AND c.name = ?
            LIMIT 1
            """,
            (server, collection_name),
        )
        return len(rows) > 0

    # ------------------------------------------------------------------
    # Alliance Rankings
    # ------------------------------------------------------------------

    def get_top10_alliances(self, server: int, collection_name: str):
        return self.db.execute(
            """
            SELECT
                re.rank,
                e.tag,
                e.name,
                re.value
            FROM ranking_entries re
            JOIN snapshots s
                ON s.id = re.snapshot_id
            JOIN collections c
                ON c.id = s.collection_id
            JOIN ranking_types rt
                ON rt.id = re.ranking_type_id
            JOIN entities e
                ON e.id = re.entity_id
            WHERE s.server = ?
              AND c.name = ?
              AND rt.name = 'alliance_power'
              AND re.rank <= 10
            ORDER BY re.rank
            """,
            (server, collection_name),
        )

    def get_latest_top10_alliances(self, server: int):
        return self.get_top10_alliances(
            server=server,
            collection_name="S6 Preseason Alliances",
        )

    def get_alliance_power_timeline(self, server: int):
        rows = self.db.execute(
            """
            SELECT
                c.name AS name,
                SUM(re.value) AS total_power
            FROM ranking_entries re
            JOIN snapshots s
                ON s.id = re.snapshot_id
            JOIN collections c
                ON c.id = s.collection_id
            JOIN ranking_types rt
                ON rt.id = re.ranking_type_id
            WHERE s.server = ?
              AND rt.name = 'alliance_power'
              AND re.rank <= 10
            GROUP BY c.name
            """,
            (server,),
        )

        order = {
            "S5 Pre Transfer": 1,
            "S5 Post Transfer": 2,
            "S6 Preseason Alliances": 3,
        }

        return sorted(rows, key=lambda row: order.get(row["name"], 999))

    # ------------------------------------------------------------------
    # Player / THP Rankings
    # ------------------------------------------------------------------

    def get_top10_players(self, server: int, collection_name: str = "S6 Preseason THP"):
        return self.db.execute(
            """
            SELECT
                re.rank,
                e.tag,
                e.name,
                re.value
            FROM ranking_entries re
            JOIN snapshots s
                ON s.id = re.snapshot_id
            JOIN collections c
                ON c.id = s.collection_id
            JOIN ranking_types rt
                ON rt.id = re.ranking_type_id
            JOIN entities e
                ON e.id = re.entity_id
            WHERE s.server = ?
              AND c.name = ?
              AND rt.name = 'total_hero_power'
              AND re.rank <= 10
            ORDER BY re.rank
            """,
            (server, collection_name),
        )

    def get_latest_top10_players(self, server: int):
        return self.get_top10_players(
            server=server,
            collection_name="S6 Preseason THP",
        )

    # ------------------------------------------------------------------
    # Cities
    # ------------------------------------------------------------------

    def get_cities(self, server: int):
        return self.db.execute(
            """
            SELECT
                cs.alliance,
                cs.city_level_1,
                cs.city_level_2,
                cs.city_level_3,
                cs.influence_points
            FROM city_stats cs
            JOIN snapshots s
                ON s.id = cs.snapshot_id
            WHERE s.server = ?
            ORDER BY cs.influence_points DESC
            """,
            (server,),
        )

    # ------------------------------------------------------------------
    # Influence
    # ------------------------------------------------------------------

    def get_influence(self, server: int):
        return self.db.execute(
            """
            SELECT
                alliance,
                faction,
                metric_name,
                value
            FROM influence_points
            WHERE server = ?
            ORDER BY alliance, metric_name
            """,
            (server,),
        )