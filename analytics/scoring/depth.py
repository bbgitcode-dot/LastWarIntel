from database.sqlite import Database
from analytics.scoring.base import BaseScore, ScoreResult


def calculate_gini(values: list[int]) -> float:
    values = sorted([v for v in values if v is not None and v >= 0])

    if not values:
        return 1.0

    n = len(values)
    total = sum(values)

    if total == 0:
        return 1.0

    weighted_sum = sum((idx + 1) * value for idx, value in enumerate(values))

    return (2 * weighted_sum) / (n * total) - (n + 1) / n


def normalize_depth_score(gini: float) -> float:
    # Gini 0.00 = perfekte Verteilung = 100 Punkte
    # Gini 0.60+ = sehr starke Konzentration = 0 Punkte
    if gini <= 0:
        return 100.0
    if gini >= 0.60:
        return 0.0

    return round((1 - (gini / 0.60)) * 100, 2)


class DepthScore(BaseScore):
    name = "depth"
    weight = 0.20

    def __init__(self):
        self.db = Database()

    def get_latest_alliance_values(self, server: int):
        rows = self.db.execute(
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
                AND rt.name = 'alliance_power'
                AND c.name = 'S6 Preseason Alliances'
                AND re.rank <= 10
            ORDER BY re.rank
            """,
            (server,),
        )

        return rows

    def calculate(self, server: int) -> ScoreResult:
        rows = self.get_latest_alliance_values(server)

        if len(rows) < 3:
            return ScoreResult(
                name=self.name,
                server=server,
                score=0.0,
                explanation="Not enough alliance depth data.",
            )

        values = [row["value"] for row in rows]
        total = sum(values)
        top1_share = values[0] / total if total else 1
        top3_share = sum(values[:3]) / total if total else 1
        gini = calculate_gini(values)
        score = normalize_depth_score(gini)

        return ScoreResult(
            name=self.name,
            server=server,
            score=score,
            raw_value=gini,
            explanation=(
                f"Top1 holds {top1_share * 100:.1f}% and Top3 hold "
                f"{top3_share * 100:.1f}% of Top10 alliance power. "
                f"Gini={gini:.3f}."
            ),
        )

    def detailed(self, server: int):
        rows = self.get_latest_alliance_values(server)

        if len(rows) < 3:
            return None

        values = [row["value"] for row in rows]
        total = sum(values)
        gini = calculate_gini(values)
        score = normalize_depth_score(gini)

        return {
            "server": server,
            "score": score,
            "gini": gini,
            "total": total,
            "top1_share": values[0] / total if total else None,
            "top3_share": sum(values[:3]) / total if total else None,
            "alliances": rows,
        }