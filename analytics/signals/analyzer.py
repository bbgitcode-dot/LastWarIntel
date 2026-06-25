"""
LastWarIntel
Signal Analyzer
Version: 1.0

Builds reusable signal contexts from existing engines.
"""

from __future__ import annotations

from analytics.events.analyzer import AllianceEventAnalyzer
from analytics.events.models import EventType, Severity
from analytics.health.analyzer import AllianceHealthAnalyzer
from analytics.recruitment.analyzer import RecruitmentTargetAnalyzer
from analytics.scoring.growth import GrowthScore
from analytics.scoring.overall import OverallScore
from analytics.scoring.player import PlayerScore
from analytics.scoring.stability import StabilityScore
from analytics.signals.models import SignalContext


class SignalAnalyzer:
    """
    Creates normalized signal contexts for one server.

    Signals are shared inputs for:
    - Executive summaries
    - President dashboard
    - Recruitment intelligence
    - Future prediction and diplomacy modules
    """

    def build(self, server: int) -> SignalContext:
        events = AllianceEventAnalyzer().analyze(server)
        health = AllianceHealthAnalyzer().analyze(server)
        recruitment = RecruitmentTargetAnalyzer().analyze_server(server)

        growth = GrowthScore().calculate(server)
        stability = StabilityScore().calculate(server)
        player = PlayerScore().calculate(server)
        overall = OverallScore().calculate(server)

        context = SignalContext(
            server=server,
            overall=overall["overall"],
            growth=growth.raw_value or 0.0,
            volatility=stability.raw_value or 0.0,
            player_score=player.score,
        )

        self._apply_event_signals(context, events)
        self._apply_health_signals(context, health)
        self._apply_recruitment_signals(context, recruitment)

        return context

    def _apply_event_signals(self, context: SignalContext, events: list) -> None:
        """
        Add event-derived signals.
        """

        context.event_count = len(events)

        for event in events:
            if event.severity == Severity.HIGH or event.severity == Severity.CRITICAL:
                context.high_impact_events += 1

            if event.severity == Severity.MEDIUM:
                context.medium_impact_events += 1

            if event.severity == Severity.LOW:
                context.low_impact_events += 1

            if event.event_type == EventType.LEFT_TOP10:
                context.left_top10_count += 1
                context.evidence.append(event.summary)

            if event.event_type == EventType.ENTERED_TOP10:
                context.entered_top10_count += 1
                context.evidence.append(event.summary)

            if event.event_type == EventType.POWER_CHANGED:
                context.power_change_count += 1

                percent = event.facts.get("percent", 0)

                if percent <= -10:
                    context.large_power_loss_count += 1
                    context.evidence.append(event.summary)

                if percent >= 15:
                    context.large_power_gain_count += 1
                    context.evidence.append(event.summary)

            if event.event_type == EventType.RANK_CHANGED:
                context.rank_change_count += 1

    def _apply_health_signals(self, context: SignalContext, health_items: list) -> None:
        """
        Add alliance-health-derived signals.
        """

        context.alliance_count = len(health_items)

        for item in health_items:
            if item.status == "Critical":
                context.critical_alliances += 1
                context.evidence.append(
                    f"{item.alliance} health is Critical."
                )

            elif item.status == "Declining":
                context.declining_alliances += 1
                context.evidence.append(
                    f"{item.alliance} health is Declining."
                )

            elif item.status == "Unstable":
                context.unstable_alliances += 1

            elif item.status == "Healthy":
                context.healthy_alliances += 1

            elif item.status == "Excellent":
                context.excellent_alliances += 1

            if item.risk == "HIGH":
                context.high_risk_alliances += 1

            elif item.risk == "MEDIUM":
                context.medium_risk_alliances += 1

            elif item.risk == "LOW":
                context.low_risk_alliances += 1

    def _apply_recruitment_signals(self, context: SignalContext, targets: list) -> None:
        """
        Add recruitment-derived signals.
        """

        context.recruitment_target_count = len(targets)

        for target in targets:
            if target.recommendation == "Contact immediately":
                context.immediate_targets += 1
                context.evidence.append(
                    f"{target.alliance} is marked as immediate recruitment target."
                )

            elif target.recommendation == "High priority":
                context.high_priority_targets += 1
                context.evidence.append(
                    f"{target.alliance} is marked as high priority recruitment target."
                )

            elif target.recommendation == "Watch":
                context.watch_targets += 1