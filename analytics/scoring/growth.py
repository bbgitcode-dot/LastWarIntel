from database.sqlite import Database


def normalize_score(percent_growth: float) -> float:
    if percent_growth <= -10:
        return 0.0
    if percent_growth >= 30:
        return 100.0

    return round(((percent_growth + 10) / 40) * 100, 2)


class GrowthScore:
    def __init__(self):
        self.db = Database()

    def get_top10_sum_by_collection(self, server: int):
        rows = self.db.execute(
            """
            SELECT
                c.name AS collection,
                SUM(re.value) AS total_power
            FROM ranking_entries re
            JOIN snapshots s ON s.id = re.snapshot_id
            JOIN collections c ON c.id = s.collection_id
            JOIN ranking_types rt ON rt.id = re.ranking_type_id
            WHERE
                s.server = ?
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

        return sorted(
            rows,
            key=lambda row: order.get(row["collection"], 999),
        )

    def calculate(self, server: int):
        rows = self.get_top10_sum_by_collection(server)

        if len(rows) < 2:
            return None

        first = rows[0]["total_power"]
        last = rows[-1]["total_power"]

        diff = last - first
        percent = (diff / first) * 100 if first else 0
        score = normalize_score(percent)

        return {
            "server": server,
            "first_collection": rows[0]["collection"],
            "last_collection": rows[-1]["collection"],
            "first_power": first,
            "last_power": last,
            "diff": diff,
            "percent": percent,
            "score": score,
            "timeline": rows,
        }