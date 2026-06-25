from analytics.scoring.base import BaseScore, ScoreResult
from services.server_repository import ServerRepository


def calculate_gini(values: list[int]) -> float:
    values = sorted([v for v in values if v is not None and v >= 0])

    if not values:
        return 1.0

    n = len(values)
    total = sum(values)

    if total == 0:
        return 1.0

    weighted_sum = sum((i + 1) * value for i, value in enumerate(values))

    return (2 * weighted_sum) / (n * total) - (n + 1) / n


def normalize_depth_score(gini: float) -> float:
    if gini <= 0:
        return 100.0

    if gini >= 0.60:
        return 0.0

    return round((1 - (gini / 0.60)) * 100, 2)


class DepthScore(BaseScore):
    name = "depth"
    weight = 0.20

    def __init__(self):
        self.repo = ServerRepository()

    def calculate(self, server: int) -> ScoreResult:

        alliances = self.repo.get_latest_top10_alliances(server)

        if len(alliances) < 3:
            return ScoreResult(
                name=self.name,
                server=server,
                score=0.0,
                explanation="Not enough alliance depth data.",
            )

        values = [a["value"] for a in alliances]

        total = sum(values)

        top1_share = values[0] / total
        top3_share = sum(values[:3]) / total

        gini = calculate_gini(values)
        score = normalize_depth_score(gini)

        return ScoreResult(
            name=self.name,
            server=server,
            score=score,
            raw_value=gini,
            explanation=(
                f"Top1 holds {top1_share*100:.1f}% "
                f"and Top3 hold {top3_share*100:.1f}% "
                f"of Top10 alliance power. "
                f"Gini={gini:.3f}."
            ),
        )

    def detailed(self, server: int):

        alliances = self.repo.get_latest_top10_alliances(server)

        if len(alliances) < 3:
            return None

        values = [a["value"] for a in alliances]

        total = sum(values)

        gini = calculate_gini(values)

        return {
            "server": server,
            "score": normalize_depth_score(gini),
            "gini": gini,
            "total": total,
            "top1_share": values[0] / total,
            "top3_share": sum(values[:3]) / total,
            "alliances": alliances,
        }