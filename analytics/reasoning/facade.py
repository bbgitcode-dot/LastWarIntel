"""
Sentinel
Reasoning Facade
"""

from __future__ import annotations

from analytics.intelligence.indicators import StrategicIndicator
from analytics.reasoning.engine import (
    RuleBasedReasoningEngine,
)
from analytics.reasoning.models import (
    IntelligenceFact,
    ReasoningContext,
    ReasoningResult,
)


class ReasoningFacade:
    """
    Public entry point for reasoning.
    """

    def __init__(self) -> None:

        self._engine = RuleBasedReasoningEngine()

    def reason(
        self,
        facts: list[IntelligenceFact],
    ) -> ReasoningResult:

        return self._engine.reason(
            facts,
        )

    def reason_context(
        self,
        facts: list[IntelligenceFact],
        indicators: list[StrategicIndicator],
    ) -> ReasoningResult:

        return self._engine.reason_context(
            ReasoningContext(
                facts=facts,
                indicators=indicators,
            )
        )