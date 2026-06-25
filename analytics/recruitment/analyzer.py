"""
LastWarIntel
Recruitment Target Analyzer
Version: 1.0

Turns alliance health assessments into actionable recruitment targets.
"""

from __future__ import annotations

from analytics.health.analyzer import AllianceHealthAnalyzer
from analytics.recruitment.models import RecruitmentTarget
from analytics.scoring.overall import OverallScore
from analytics.scoring.player import PlayerScore
from services.server_repository import ServerRepository


class RecruitmentTargetAnalyzer:
    """
    Builds actionable recruitment targets from Alliance Health.

    This analyzer does not calculate alliance health itself.
    It consumes AllianceHealthAnalyzer results and adds recruitment priority.
    """

    def __init__(self):
        self.repo = ServerRepository()
        self.health_analyzer = AllianceHealthAnalyzer()
        self.overall_score = OverallScore()
        self.player_score = PlayerScore()

    def analyze_server(self, server: int) -> list[RecruitmentTarget]:
        """
        Analyze one server and return recruitment targets.
        """

        alliance_health = self.health_analyzer.analyze(server)

        overall = self.overall_score.calculate(server)["overall"]
        player = self.player_score.calculate(server).score

        targets: list[RecruitmentTarget] = []

        for health in alliance_health:
            target = self._build_target(
                server=server,
                health=health,
                overall=overall,
                player=player,
            )

            if target.priority > 0:
                targets.append(target)

        return sorted(
            targets,
            key=lambda item: item.priority,
            reverse=True,
        )

    def analyze_all(self) -> list[RecruitmentTarget]:
        """
        Analyze all servers with complete scoring data.
        """

        targets: list[RecruitmentTarget] = []

        for row in self.repo.get_all_servers():
            server = row["server"]

            if not self.repo.has_complete_scoring_data(server):
                continue

            targets.extend(self.analyze_server(server))

        return sorted(
            targets,
            key=lambda item: item.priority,
            reverse=True,
        )

    def _build_target(
        self,
        server: int,
        health,
        overall: float,
        player: float,
    ) -> RecruitmentTarget:
        """
        Convert one AllianceHealth object into a RecruitmentTarget.
        """

        priority = 0
        confidence = 40.0
        reasons: list[str] = []

        if health.score < 30:
            priority += 40
            confidence += 20
            reasons.append("Alliance health is critical.")
        elif health.score < 50:
            priority += 25
            confidence += 15
            reasons.append("Alliance health is declining.")
        elif health.score < 70:
            priority += 10
            confidence += 8
            reasons.append("Alliance health is unstable.")

        if health.status == "Critical":
            priority += 20
            confidence += 15
            reasons.append("Status is Critical.")
        elif health.status == "Declining":
            priority += 10
            confidence += 10
            reasons.append("Status is Declining.")

        if health.trend == "Declining":
            priority += 15
            confidence += 10
            reasons.append("Trend is declining.")
        elif health.trend == "Mixed":
            priority += 5
            reasons.append("Trend is mixed.")

        if health.risk == "HIGH":
            priority += 15
            confidence += 10
            reasons.append("Recruitment risk signal is HIGH.")
        elif health.risk == "MEDIUM":
            priority += 5
            reasons.append("Recruitment risk signal is MEDIUM.")

        if overall >= 55:
            priority += 10
            confidence += 5
            reasons.append("Server is relevant enough for active diplomacy.")

        if player >= 65:
            priority += 10
            confidence += 5
            reasons.append("Server has a strong player base.")

        for reason in health.reasons:
            reasons.append(reason)

        priority = max(0, min(priority, 100))
        confidence = max(0.0, min(confidence, 100.0))

        return RecruitmentTarget(
            server=server,
            alliance=health.alliance,
            priority=priority,
            confidence=round(confidence, 2),
            health=health.score,
            health_status=health.status,
            trend=health.trend,
            risk=health.risk,
            recommendation=self._recommendation(priority),
            reasons=reasons,
        )

    @staticmethod
    def _recommendation(priority: int) -> str:
        """
        Convert priority score into a practical action.
        """

        if priority >= 85:
            return "Contact immediately"

        if priority >= 70:
            return "High priority"

        if priority >= 50:
            return "Monitor closely"

        if priority >= 30:
            return "Watch"

        return "Ignore"