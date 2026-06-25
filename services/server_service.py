from collections import defaultdict
from database.sqlite import Database


class ServerService:
    def __init__(self):
        self.db = Database()

    def get_collections(self, server: int):
        return self.db.execute(
            """
            SELECT DISTINCT
                c.id,
                c.name,
                c.type
            FROM collections c
            JOIN snapshots s
                ON s.collection_id = c.id
            WHERE s.server = ?
            ORDER BY c.created_at
            """,
            (server,),
        )

    def get_snapshots(self, server: int):
        return self.db.execute(
            """
            SELECT
                s.id,
                s.server,
                c.name AS collection,
                c.type,
                s.created_at
            FROM snapshots s
            JOIN collections c
                ON c.id = s.collection_id
            WHERE s.server = ?
            ORDER BY c.created_at
            """,
            (server,),
        )

    def get_top_alliances(self, server: int, limit_per_collection: int = 10):
        rows = self.db.execute(
            """
            SELECT
                c.name AS collection,
                c.created_at AS collection_created_at,
                re.rank,
                e.tag,
                e.name,
                re.value
            FROM ranking_entries re
            JOIN entities e
                ON e.id = re.entity_id
            JOIN snapshots s
                ON s.id = re.snapshot_id
            JOIN collections c
                ON c.id = s.collection_id
            JOIN ranking_types rt
                ON rt.id = re.ranking_type_id
            WHERE
                s.server = ?
                AND rt.name = 'alliance_power'
            ORDER BY
                c.created_at,
                re.rank
            """,
            (server,),
        )

        return self._limit_per_collection(rows, limit_per_collection)

    def get_top_players(self, server: int, limit_per_collection: int = 10):
        rows = self.db.execute(
            """
            SELECT
                c.name AS collection,
                c.created_at AS collection_created_at,
                re.rank,
                e.tag,
                e.name,
                re.value
            FROM ranking_entries re
            JOIN entities e
                ON e.id = re.entity_id
            JOIN snapshots s
                ON s.id = re.snapshot_id
            JOIN collections c
                ON c.id = s.collection_id
            JOIN ranking_types rt
                ON rt.id = re.ranking_type_id
            WHERE
                s.server = ?
                AND rt.name = 'total_hero_power'
            ORDER BY
                c.created_at,
                re.rank
            """,
            (server,),
        )

        return self._limit_per_collection(rows, limit_per_collection)

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
            ORDER BY
                c.created_at,
                m.metric_name
            """,
            (server,),
        )

    def get_cities(self, server: int):
        return self.db.execute(
            """
            SELECT
                alliance,
                city_level_1,
                city_level_2,
                city_level_3,
                influence_points
            FROM city_stats cs
            JOIN snapshots s
                ON s.id = cs.snapshot_id
            WHERE s.server = ?
            ORDER BY influence_points DESC
            """,
            (server,),
        )

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

    def get_server_overview(self, server: int):
        return {
            "collections": self.get_collections(server),
            "snapshots": self.get_snapshots(server),
            "alliances": self.get_top_alliances(server),
            "players": self.get_top_players(server),
            "metrics": self.get_metrics(server),
            "cities": self.get_cities(server),
            "influence": self.get_influence(server),
        }

    @staticmethod
    def _limit_per_collection(rows, limit: int):
        grouped = defaultdict(list)

        for row in rows:
            grouped[row["collection"]].append(row)

        limited = []

        for collection_rows in grouped.values():
            limited.extend(collection_rows[:limit])

        return limited