from database.sqlite import Database


class ServerRepository:
    def __init__(self):
        self.db = Database()

    # ------------------------------------------------------------------
    # Server / Collections
    # ------------------------------------------------------------------

    def get_all_servers(self):
        return self.db.execute(
            """
            SELECT DISTINCT server
            FROM snapshots
            ORDER BY server
            """
        )

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

    def get_collections_for_server(self, server: int):
        return self.db.execute(
            """
            SELECT DISTINCT
                c.id,
                c.name,
                c.type,
                c.created_at
            FROM collections c
            JOIN snapshots s
                ON s.collection_id = c.id
            WHERE s.server = ?
            ORDER BY c.created_at
            """,
            (server,),
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
    # Alliance Power
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
            "S4 Server Summary": 1,
            "S5 Pre Transfer": 2,
            "S5 Post Transfer": 3,
            "S6 Preseason Alliances": 4,
        }

        return sorted(rows, key=lambda row: order.get(row["name"], 999))

    def get_latest_top10_alliance_power_sum(self, server: int):
        alliances = self.get_latest_top10_alliances(server)
        return sum(row["value"] for row in alliances)

    # ------------------------------------------------------------------
    # Player / THP
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

    def get_latest_top10_player_power_sum(self, server: int):
        players = self.get_latest_top10_players(server)
        return sum(row["value"] for row in players)

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def get_metrics(self, server: int):
        return self.db.execute(
            """
            SELECT
                c.name AS collection,
                m.metric_name,
                m.value
            FROM metrics m
            JOIN snapshots s
                ON s.id = m.snapshot_id
            JOIN collections c
                ON c.id = s.collection_id
            WHERE s.server = ?
            ORDER BY c.created_at, m.metric_name
            """,
            (server,),
        )

    def get_metric(self, server: int, collection_name: str, metric_name: str):
        rows = self.db.execute(
            """
            SELECT
                m.value
            FROM metrics m
            JOIN snapshots s
                ON s.id = m.snapshot_id
            JOIN collections c
                ON c.id = s.collection_id
            WHERE s.server = ?
              AND c.name = ?
              AND m.metric_name = ?
            LIMIT 1
            """,
            (server, collection_name, metric_name),
        )

        return rows[0]["value"] if rows else None

    # ------------------------------------------------------------------
    # Data Availability
    # ------------------------------------------------------------------

    def has_latest_alliance_data(self, server: int) -> bool:
        return self.has_collection(server, "S6 Preseason Alliances")

    def has_latest_player_data(self, server: int) -> bool:
        return self.has_collection(server, "S6 Preseason THP")

    def has_growth_data(self, server: int) -> bool:
        timeline = self.get_alliance_power_timeline(server)
        return len(timeline) >= 2

    def has_complete_scoring_data(self, server: int) -> bool:
        return (
            self.has_growth_data(server)
            and self.has_latest_alliance_data(server)
            and self.has_latest_player_data(server)
        )