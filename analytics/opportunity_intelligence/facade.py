"""
Sentinel
Opportunity Intelligence Facade
"""

from __future__ import annotations

from analytics.opportunity_intelligence.analyzer import (
    OpportunityIntelligenceAnalyzer,
)
from analytics.opportunity_intelligence.models import (
    OpportunityContext,
)


class OpportunityIntelligenceFacade:
    """
    Public entry point for opportunity intelligence.
    """

    def __init__(
        self,
    ) -> None:

        self._analyzer = OpportunityIntelligenceAnalyzer()

    def analyze(
        self,
        context: OpportunityContext,
    ):

        return self._analyzer.analyze(
            context,
        )