"""
Sentinel
Recruitment Advisor Builder
"""

from __future__ import annotations

from analytics.intelligence.indicators import StrategicIndicator
from analytics.opportunity_intelligence.facade import (
    OpportunityIntelligenceFacade,
)
from analytics.opportunity_intelligence.models import (
    OpportunityContext,
    OpportunityType,
)
from analytics.reasoning.models import IntelligenceFact

from application.recruitment_advisor.models import (
    RecruitmentAdvisorResult,
    RecruitmentTarget,
)
from application.recruitment_advisor.ranking import (
    RecruitmentTargetRanker,
)


class RecruitmentAdvisorBuilder:
    """
    Builds recruitment advice from facts and strategic indicators.
    """

    def __init__(
        self,
    ) -> None:

        self._opportunity = OpportunityIntelligenceFacade()
        self._ranker = RecruitmentTargetRanker()

    def build(
        self,
        server: int,
        alliance: str,
        facts: list[IntelligenceFact],
        indicators: list[StrategicIndicator],
    ) -> RecruitmentAdvisorResult:

        context = OpportunityContext(
            server=server,
            alliance=alliance,
            facts=facts,
            indicators=indicators,
        )

        opportunities = self._opportunity.analyze(
            context,
        )

        targets: list[RecruitmentTarget] = []

        for opportunity in opportunities:

            if opportunity.opportunity_type != OpportunityType.RECRUITMENT:
                continue

            targets.append(
                RecruitmentTarget(
                    name=alliance,
                    server=server,
                    alliance=alliance,
                    score=opportunity.score,
                    priority=opportunity.priority.value,
                    summary=opportunity.description,
                    evidence=opportunity.evidence,
                    facts=facts,
                    opportunity=opportunity,
                )
            )

        ranked = self._ranker.rank(
            targets,
        )

        return RecruitmentAdvisorResult(
            server=server,
            targets=ranked,
            recommendation=self._recommendation(
                ranked,
            ),
        )

    @staticmethod
    def _recommendation(
        targets: list[RecruitmentTarget],
    ) -> str:

        if not targets:
            return "No recruitment target should be prioritized right now."

        top = targets[0]

        if top.score >= 85:
            return f"Prioritize {top.name} immediately."

        if top.score >= 65:
            return f"Prepare outreach for {top.name}."

        return f"Monitor {top.name} and verify with the next snapshot."