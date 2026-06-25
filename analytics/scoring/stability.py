from statistics import mean, pstdev

from analytics.scoring.base import BaseScore, ScoreResult
from services.server_repository import ServerRepository


def normalize_stability_score(volatility_percent: float) -> float:
    """
    0% volatility  -> 100 Punkte
    25% volatility -> 0 Punkte
    """

    if volatility_percent <= 0:
        return 100.0

    if volatility_percent >= 25:
        return 0.0

    return round((1 - (volatility_percent / 25)) * 100, 2)


class StabilityScore(BaseScore):
    name = "stability"
    weight = 0.10

    def __init__(self):
        self.repo = ServerRepository()

    def calculate(self, server: int) -> ScoreResult:
        timeline = self.repo.get_alliance_power_timeline(server)

        if len(timeline) < 3:
            return ScoreResult(
                name=self.name,
                server=server,
                score=0.0,
                explanation="Not enough timeline data for stability calculation.",
            )

        values = [row["total_power"] for row in timeline]
        avg = mean(values)
        deviation = pstdev(values)

        volatility_percent = (deviation / avg) * 100 if avg else 100
        score = normalize_stability_score(volatility_percent)

        return ScoreResult(
            name=self.name,
            server=server,
            score=score,
            raw_value=volatility_percent,
            explanation=(
                f"Top10 alliance power volatility is "
                f"{volatility_percent:.2f}% across {len(values)} snapshots."
            ),
        )

    def detailed(self, server: int):
        timeline = self.repo.get_alliance_power_timeline(server)

        if len(timeline) < 3:
            return None

        values = [row["total_power"] for row in timeline]
        avg = mean(values)
        deviation = pstdev(values)

        volatility_percent = (deviation / avg) * 100 if avg else 100
        score = normalize_stability_score(volatility_percent)

        changes = []

        for idx in range(1, len(timeline)):
            previous = timeline[idx - 1]
            current = timeline[idx]

            old_value = previous["total_power"]
            new_value = current["total_power"]
            diff = new_value - old_value
            percent = (diff / old_value) * 100 if old_value else 0

            changes.append(
                {
                    "from": previous["name"],
                    "to": current["name"],
                    "old_value": old_value,
                    "new_value": new_value,
                    "diff": diff,
                    "percent": percent,
                }
            )

        return {
            "server": server,
            "score": score,
            "average_power": avg,
            "standard_deviation": deviation,
            "volatility_percent": volatility_percent,
            "timeline": timeline,
            "changes": changes,
        }