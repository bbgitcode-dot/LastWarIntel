from database.sqlite import Database


class ServerRepository:
    def __init__(self):
        self.db = Database()

    # ------------------------------------------------------------------
    # Alliance Rankings
    # ------------------------------------------------------------------

    def get_top10_alliances(self, server: int, collection: str):
        return self.db.execute(
            """
            SELECT
                re.rank,
                e.tag,
                e.name,
                re.value
            FROM ranking_entries re
            JOIN snapshots s ON s.id = re.snapshot_id
            JOIN collections c ON c.id = s.collection_id
            JOIN ranking_types rt ON rt.id = re.ranking_type_id
            JOIN entities e ON e.id = re.entity_id
            WHERE
                s.server = ?
                AND c.name = ?
                AND rt.name = 'alliance_power'
                AND re.rank <= 10
            ORDER BY re.rank
            """,
            (server, collection),
        )

    def get_latest_top10_alliances(self, server: int):
        return self.get_top10_alliances(
            server,
            "S6 Preseason Alliances"
        )

    # ------------------------------------------------------------------
    # THP
    # ------------------------------------------------------------------

    def get_top10_players(self, server: int):
        return self.db.execute(
            """
            SELECT
                re.rank,
                e.tag,
                e.name,
                re.value
            FROM ranking_entries re
            JOIN snapshots s ON s.id = re.snapshot_id
            JOIN collections c ON c.id = s.collection_id
            JOIN ranking_types rt ON rt.id = re.ranking_type_id
            JOIN entities e ON e.id = re.entity_id
            WHERE
                s.server = ?
                AND c.name = 'S6 Preseason THP'
                AND rt.name = 'total_hero_power'
                AND re.rank <= 10
            ORDER BY re.rank
            """,
            (server,),
        )

    # ------------------------------------------------------------------
    # Timeline
    # ------------------------------------------------------------------

    def get_alliance_power_timeline(self, server: int):
        rows = self.db.execute(
            """
            SELECT
                c.name,
                SUM(re.value) AS total_power
            FROM ranking_entries re
            JOIN snapshots s ON s.id = re.snapshot_id
            JOIN collections c ON c.id = s.collection_id
            JOIN ranking_types rt ON rt.id = re.ranking_type_id
            WHERE
                s.server = ?
                AND rt.name='alliance_power'
                AND re.rank<=10
            GROUP BY c.name
            """,
            (server,),
        )

        order = {
            "S5 Pre Transfer": 1,
            "S5 Post Transfer": 2,
            "S6 Preseason Alliances": 3,
        }

        return sorted(rows, key=lambda r: order.get(r["name"], 999))

    # ------------------------------------------------------------------
    # Cities
    # ------------------------------------------------------------------

    def get_cities(self, server: int):
        return self.db.execute(
            """
            SELECT *
            FROM cities
            WHERE server=?
            ORDER BY influence DESC
            """,
            (server,),
        )

    # ------------------------------------------------------------------
    # Influence
    # ------------------------------------------------------------------

    def get_influence(self, server: int):
        return self.db.execute(
            """
            SELECT *
            FROM influence_points
            WHERE server=?
            ORDER BY alliance
            """,
            (server,),
        )

    # ------------------------------------------------------------------
    # Collections
    # ------------------------------------------------------------------

    def has_collection(self, server: int, collection: str):
        rows = self.db.execute(
            """
            SELECT 1
            FROM snapshots s
            JOIN collections c
                ON c.id=s.collection_id
            WHERE
                s.server=?
                AND c.name=?
            LIMIT 1
            """,
            (server, collection),
        )

        return len(rows) > 0