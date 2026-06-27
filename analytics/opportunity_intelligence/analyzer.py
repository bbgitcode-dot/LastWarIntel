"""
Sentinel
Opportunity Intelligence Analyzer
"""

from __future__ import annotations

from analytics.opportunity_intelligence.models import (
    OpportunityAssessment,
    OpportunityContext,
    OpportunityPriority,
    OpportunityType,
)


class OpportunityIntelligenceAnalyzer:
    """
    Evaluates strategic opportunities from facts and indicators.
    """

    def analyze(
        self,
        context: OpportunityContext,
    ) -> list[OpportunityAssessment]:

        opportunities: list[OpportunityAssessment] = []

        recruitment = self._recruitment_opportunity(
            context,
        )

        if recruitment is not None:
            opportunities.append(
                recruitment,
            )

        return opportunities

    def _recruitment_opportunity(
        self,
        context: OpportunityContext,
    ) -> OpportunityAssessment | None:

        recruitability = self._indicator_value(
            context,
            "Recruitability",
        )

        structural_health = self._indicator_value(
            context,
            "Structural Health",
        )

        whale_facts = self._facts_by_tag(
            context,
            "whale",
        )

        decline_facts = self._facts_by_tag(
            context,
            "decline",
        )

        score = min(
            recruitability * 0.55
            + max(0, 100 - structural_health) * 0.25
            + len(whale_facts) * 8
            + len(decline_facts) * 10,
            100,
        )

        if score < 35:
            return None

        evidence = []

        if recruitability:
            evidence.append(
                f"Recruitability indicator: {recruitability:.0f}."
            )

        if structural_health:
            evidence.append(
                f"Structural health indicator: {structural_health:.0f}."
            )

        for fact in whale_facts[:3]:
            evidence.append(
                fact.description,
            )

        for fact in decline_facts[:3]:
            evidence.append(
                fact.description,
            )

        return OpportunityAssessment(
            title="Recruitment Opportunity",
            description=(
                "The current intelligence suggests potential recruitment leverage."
            ),
            opportunity_type=OpportunityType.RECRUITMENT,
            priority=self._priority_from_score(
                score,
            ),
            score=round(score, 2),
            confidence=self._confidence(
                context,
            ),
            evidence=evidence,
            tags=[
                "recruitment",
                "opportunity",
            ],
        )

    @staticmethod
    def _indicator_value(
        context: OpportunityContext,
        title: str,
    ) -> float:

        for indicator in context.indicators:
            if indicator.title == title:
                return indicator.value

        return 0.0

    @staticmethod
    def _facts_by_tag(
        context: OpportunityContext,
        tag: str,
    ):

        normalized = tag.casefold()

        return [
            fact
            for fact in context.facts
            if any(
                item.casefold() == normalized
                for item in fact.tags
            )
        ]

    @staticmethod
    def _priority_from_score(
        score: float,
    ) -> OpportunityPriority:

        if score >= 85:
            return OpportunityPriority.CRITICAL

        if score >= 65:
            return OpportunityPriority.HIGH

        if score >= 35:
            return OpportunityPriority.MEDIUM

        return OpportunityPriority.LOW

    @staticmethod
    def _confidence(
        context: OpportunityContext,
    ) -> float:

        if not context.facts:
            return 70.0

        return round(
            sum(fact.confidence for fact in context.facts)
            / len(context.facts),
            2,
        )