"""
Sentinel
Opportunity Provider
"""

from __future__ import annotations

from analytics.opportunity_intelligence.facade import (
    OpportunityIntelligenceFacade,
)
from analytics.opportunity_intelligence.models import (
    OpportunityAssessment,
    OpportunityContext,
)


class OpportunityProvider:
    """
    Provides strategic opportunity assessments.
    """

    @property
    def entity_name(
        self,
    ) -> str:

        return "Opportunity"

    def __init__(
        self,
    ) -> None:

        self._facade = OpportunityIntelligenceFacade()

    def analyze(
        self,
        context: OpportunityContext,
    ) -> list[OpportunityAssessment]:

        return self._facade.analyze(
            context,
        )