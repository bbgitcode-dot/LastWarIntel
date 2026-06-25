from database.sqlite import Database
from analytics.scoring.base import BaseScore, ScoreResult


def normalize_power_score(power: int) -> float:
    # 250B+ = absoluter Spitzenbereich
    if power >= 250_000_000_000:
        return 100.0

    # 50B oder weniger = schwach
    if power <= 50_000_000_000:
        return 0.0

    return round(((power - 50_000_000_000) / 200_000_000_000) * 100, 2)


class PowerScore(BaseScore):
    name = "power"
    weight = 0.35

    def __init__(self):
        self.db = Database()

    def get_latest_top10_power(self, server: int):
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
                AND c.name = 'S6 Preseason Alliances'
            GROUP BY c.name
            """,
            (server,),
        )

        return rows[0] if rows else None

    def calculate(self, server: int) -> ScoreResult:
        row = self.get_latest_top10_power(server)

        if not row:
            return ScoreResult(
                name=self.name,
                server=server,
                score=0.0,
                explanation="No latest alliance power data found.",
            )

        power = row["total_power"]
        score = normalize_power_score(power)

        return ScoreResult(
            name=self.name,
            server=server,
            score=score,
            raw_value=power,
            explanation=f"Latest Top10 alliance power is {power}.",
        )