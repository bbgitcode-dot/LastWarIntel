from analytics.scoring.base import BaseScore, ScoreResult
from services.server_repository import ServerRepository


def normalize_power_score(power: int) -> float:
    """
    50B  -> 0 Punkte
    250B -> 100 Punkte
    """

    if power <= 50_000_000_000:
        return 0.0

    if power >= 250_000_000_000:
        return 100.0

    return round(((power - 50_000_000_000) / 200_000_000_000) * 100, 2)


class PowerScore(BaseScore):
    name = "power"
    weight = 0.35

    def __init__(self):
        self.repo = ServerRepository()

    def calculate(self, server: int) -> ScoreResult:

        alliances = self.repo.get_latest_top10_alliances(server)

        if not alliances:
            return ScoreResult(
                name=self.name,
                server=server,
                score=0.0,
                explanation="No alliance power data available."
            )

        total_power = sum(a["value"] for a in alliances)

        score = normalize_power_score(total_power)

        return ScoreResult(
            name=self.name,
            server=server,
            score=score,
            raw_value=total_power,
            explanation=f"Latest Top10 alliance power is {total_power:,}."
        )

    def detailed(self, server: int):

        alliances = self.repo.get_latest_top10_alliances(server)

        if not alliances:
            return None

        total_power = sum(a["value"] for a in alliances)

        return {
            "server": server,
            "score": normalize_power_score(total_power),
            "total_power": total_power,
            "alliances": alliances
        }