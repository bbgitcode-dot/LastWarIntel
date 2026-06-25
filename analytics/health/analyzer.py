"""
LastWarIntel
Alliance Health Analyzer
Version: 1.0

Turns alliance events into alliance health assessments.
"""

from collections import defaultdict

from analytics.events.analyzer import AllianceEventAnalyzer
from analytics.events.models import Event, EventType
from analytics.health.models import AllianceHealth
from services.server_repository import ServerRepository


class AllianceHealthAnalyzer:
    def __init__(self):
        self.repo = ServerRepository()
        self.event_analyzer = AllianceEventAnalyzer()

    def analyze(self, server: int) -> list[AllianceHealth]:
        histories = self.repo.get_all_alliance_histories(server)
        events = self.event_analyzer.analyze(server)

        events_by_alliance = self._group_events(events)

        results = []

        for alliance in sorted(histories.keys()):
            alliance_events = events_by_alliance.get(alliance, [])
            health = self._calculate_health(
                server=server,
                alliance=alliance,
                events=alliance_events,
                history=histories[alliance],
            )
            results.append(health)

        return sorted(results, key=lambda item: item.score)

    @staticmethod
    def _group_events(events: list[Event]) -> dict[str, list[Event]]:
        grouped = defaultdict(list)

        for event in events:
            grouped[event.entity].append(event)

        return dict(grouped)

    def _calculate_health(self, server: int, alliance: str, events: list[Event], history) -> AllianceHealth:
        score = 70
        reasons = []
        facts = {}

        latest_collection = self._latest_collection(server)

        first = history[0] if history else None
        last = history[-1] if history else None

        if first and last:
            facts["first_collection"] = first["collection"]
            facts["last_collection"] = last["collection"]
            facts["first_rank"] = first["rank"]
            facts["last_rank"] = last["rank"]
            facts["first_power"] = first["power"]
            facts["last_power"] = last["power"]

        for event in events:
            if event.event_type == EventType.LEFT_TOP10:
                score -= 45
                reasons.append("Alliance left the latest Top10.")

            if event.event_type == EventType.ENTERED_TOP10:
                score += 18
                reasons.append("Alliance entered the latest Top10.")

            if event.event_type == EventType.POWER_CHANGED:
                percent = event.facts.get("percent", 0)

                if percent >= 25:
                    score += 20
                    reasons.append(f"Strong power growth detected: +{percent:.2f}%.")
                elif percent >= 10:
                    score += 10
                    reasons.append(f"Moderate power growth detected: +{percent:.2f}%.")

                if percent <= -25:
                    score -= 30
                    reasons.append(f"Severe power loss detected: {percent:.2f}%.")
                elif percent <= -10:
                    score -= 18
                    reasons.append(f"Power loss detected: {percent:.2f}%.")

            if event.event_type == EventType.RANK_CHANGED:
                delta = event.facts.get("rank_delta", 0)

                if delta >= 3:
                    score += 8
                    reasons.append(f"Alliance climbed {delta} ranks.")
                elif delta <= -3:
                    score -= 12
                    reasons.append(f"Alliance dropped {abs(delta)} ranks.")

        if last and latest_collection and last["collection"] != latest_collection:
            score -= 20
            reasons.append("Alliance is missing from the latest available snapshot.")

        score = max(0, min(score, 100))

        status = self._status(score)
        trend = self._trend(events)
        risk = self._risk(score)

        if not reasons:
            reasons.append("No major health-changing events detected.")

        return AllianceHealth(
            server=server,
            alliance=alliance,
            score=score,
            status=status,
            trend=trend,
            risk=risk,
            reasons=reasons,
            events=events,
            facts=facts,
        )

    def _latest_collection(self, server: int) -> str | None:
        timeline = self.repo.get_alliance_power_timeline(server)

        if not timeline:
            return None

        return timeline[-1]["name"]

    @staticmethod
    def _status(score: int) -> str:
        if score >= 85:
            return "Excellent"
        if score >= 70:
            return "Healthy"
        if score >= 50:
            return "Unstable"
        if score >= 30:
            return "Declining"
        return "Critical"

    @staticmethod
    def _risk(score: int) -> str:
        if score >= 75:
            return "LOW"
        if score >= 50:
            return "MEDIUM"
        return "HIGH"

    @staticmethod
    def _trend(events: list[Event]) -> str:
        power_events = [
            event for event in events
            if event.event_type == EventType.POWER_CHANGED
        ]

        if not power_events:
            return "Stable"

        total = sum(event.facts.get("percent", 0) for event in power_events)

        if total >= 15:
            return "Growing"
        if total <= -15:
            return "Declining"
        return "Mixed"