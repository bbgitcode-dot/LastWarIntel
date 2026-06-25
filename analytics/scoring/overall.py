from analytics.scoring.growth import GrowthScore
from analytics.scoring.power import PowerScore
from analytics.scoring.depth import DepthScore
from analytics.scoring.player import PlayerScore
from analytics.scoring.stability import StabilityScore


class OverallScore:
    def __init__(self):
        self.scorers = [
            GrowthScore(),
            PowerScore(),
            DepthScore(),
            PlayerScore(),
            StabilityScore(),
        ]

    def calculate(self, server: int):
        results = [scorer.calculate(server) for scorer in self.scorers]

        total_weight = sum(scorer.weight for scorer in self.scorers)

        weighted = 0.0
        for scorer, result in zip(self.scorers, results):
            weighted += scorer.weight * result.score

        overall = round(weighted / total_weight, 2)

        return {
            "server": server,
            "overall": overall,
            "details": results,
        }