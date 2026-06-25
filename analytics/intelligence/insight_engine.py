"""
LastWarIntel
Insight Engine
Version: 1.0

Builds high-level insights from reusable server signals.
"""

from __future__ import annotations

from analytics.intelligence.insight_rules import InsightRuleEngine
from analytics.intelligence.models import Insight
from analytics.signals.analyzer import SignalAnalyzer


class InsightEngine:
    """
    Creates high-level insights for one server.
    """

    def __init__(self):
        self.signal_analyzer = SignalAnalyzer()
        self.rule_engine = InsightRuleEngine()

    def analyze(self, server: int) -> list[Insight]:
        """
        Build signal context and evaluate insight rules.
        """

        signals = self.signal_analyzer.build(server)
        insights = self.rule_engine.evaluate(signals)

        return sorted(
            insights,
            key=lambda insight: (
                -insight.severity.value,
                -insight.confidence,
                insight.title,
            ),
        )