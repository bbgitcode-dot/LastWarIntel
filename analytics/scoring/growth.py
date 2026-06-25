from analytics.scoring.base import BaseScore, ScoreResult
from services.server_repository import ServerRepository


def normalize_score(percent_growth: float) -> float:
    if percent_growth <= -10:
        return 0.0
    if percent_growth >= 30:
        return 100.0

    return round(((percent_growth + 10) / 40) * 100, 2)


class GrowthScore(BaseScore):
    name = "growth"
    weight = 0.30

    def __init__(self):
        self.repo = ServerRepository()

    def calculate(self, server: int) -> ScoreResult:
        rows = self.repo.get_alliance_power_timeline(server)

        if len(rows) < 2:
            return ScoreResult(
                name=self.name,
                server=server,
                score=0.0,
                explanation="Not enough historical alliance data.",
            )

        first = rows[0]["total_power"]
        last = rows[-1]["total_power"]

        diff = last - first
        percent = (diff / first) * 100 if first else 0
        score = normalize_score(percent)

        return ScoreResult(
            name=self.name,
            server=server,
            score=score,
            raw_value=percent,
            explanation=f"Top10 alliance power changed by {percent:+.2f}%.",
        )

    def detailed(self, server: int):
        rows = self.repo.get_alliance_power_timeline(server)

        if len(rows) < 2:
            return None

        first = rows[0]["total_power"]
        last = rows[-1]["total_power"]
        diff = last - first
        percent = (diff / first) * 100 if first else 0

        return {
            "server": server,
            "first_collection": rows[0]["name"],
            "last_collection": rows[-1]["name"],
            "first_power": first,
            "last_power": last,
            "diff": diff,
            "percent": percent,
            "score": normalize_score(percent),
            "timeline": rows,
        }