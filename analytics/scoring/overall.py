from analytics.scoring.base import ScoreResult
from analytics.scoring.growth import GrowthScore
from analytics.scoring.power import PowerScore


class OverallScore:
    def __init__(self):
        self.scorers = [
            GrowthScore(),
            PowerScore(),
        ]

    def calculate(self, server: int):
        results = [scorer.calculate(server) for scorer in self.scorers]

        total_weight = sum(scorer.weight for scorer in self.scorers)
        weighted_score = 0.0

        for scorer, result in zip(self.scorers, results):
            weighted_score += result.score * scorer.weight

        overall = round(weighted_score / total_weight, 2) if total_weight else 0.0

        return {
            "server": server,
            "overall": overall,
            "details": results,
        }