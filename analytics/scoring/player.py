from statistics import median

from analytics.scoring.base import BaseScore, ScoreResult
from services.server_repository import ServerRepository


def normalize_player_score(avg_thp: float) -> float:
    """
    180M -> 0
    350M -> 100
    """

    minimum = 180_000_000
    maximum = 350_000_000

    if avg_thp <= minimum:
        return 0.0

    if avg_thp >= maximum:
        return 100.0

    return round(((avg_thp - minimum) / (maximum - minimum)) * 100, 2)


class PlayerScore(BaseScore):

    name = "player"
    weight = 0.15

    def __init__(self):
        self.repo = ServerRepository()

    def calculate(self, server: int):

        players = self.repo.get_latest_top10_players(server)

        if len(players) < 5:
            return ScoreResult(
                name=self.name,
                server=server,
                score=0,
                explanation="Not enough player data."
            )

        values = [p["value"] for p in players]

        average = sum(values) / len(values)

        elite300 = sum(v >= 300_000_000 for v in values)
        elite320 = sum(v >= 320_000_000 for v in values)
        elite350 = sum(v >= 350_000_000 for v in values)

        score = normalize_player_score(average)

        return ScoreResult(
            name=self.name,
            server=server,
            score=score,
            raw_value=average,
            explanation=(
                f"Average THP {average:,.0f}. "
                f"{elite300} players above 300M, "
                f"{elite320} above 320M, "
                f"{elite350} above 350M."
            )
        )

    def detailed(self, server):

        players = self.repo.get_latest_top10_players(server)

        if len(players) < 5:
            return None

        values = [p["value"] for p in players]

        return {
            "players": players,
            "sum": sum(values),
            "average": sum(values) / len(values),
            "median": median(values),
            "highest": max(values),
            "lowest": min(values),
            "spread": max(values) - min(values),
            "elite300": sum(v >= 300_000_000 for v in values),
            "elite320": sum(v >= 320_000_000 for v in values),
            "elite350": sum(v >= 350_000_000 for v in values),
            "score": normalize_player_score(sum(values) / len(values)),
        }