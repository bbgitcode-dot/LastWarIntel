"""
Sentinel
Watchlist Builder
"""

from __future__ import annotations

from uuid import uuid4

from analytics.intelligence.indicators import StrategicIndicator
from analytics.opportunity_intelligence.models import (
    OpportunityAssessment,
    OpportunityPriority,
    OpportunityType,
)
from analytics.reasoning.models import IntelligenceFact
from analytics.talent_intelligence.recruitment_value import RecruitmentValue

from application.assessments.models import Assessment
from application.watchlist.decision_snapshot import (
    DecisionSnapshot,
)
from application.watchlist.models import (
    WatchEntityType,
    WatchPriority,
    WatchTarget,
)
from application.watchlist.status import (
    WatchStatus,
)


class WatchlistBuilder:
    """
    Builds watch targets from strategic opportunities.
    """

    def build_from_opportunities(
        self,
        server: int,
        alliance: str | None,
        opportunities: list[OpportunityAssessment],
        indicators: list[StrategicIndicator],
        facts: list[IntelligenceFact],
        assessment: Assessment | None = None,
        recruitment_value: RecruitmentValue | None = None,
    ) -> list[WatchTarget]:

        targets: list[WatchTarget] = []

        for opportunity in opportunities:
            if opportunity.opportunity_type != OpportunityType.RECRUITMENT:
                continue

            snapshot = self._decision_snapshot(
                opportunity,
                indicators,
                facts,
            )

            targets.append(
                WatchTarget(
                    id=str(uuid4()),
                    entity_type=WatchEntityType.ALLIANCE,
                    server=server,
                    alliance=alliance,
                    name=alliance or "Unknown Alliance",
                    priority=self._priority(
                        opportunity.priority,
                    ),
                    score=opportunity.score,
                    reason=opportunity.description,
                    tags=list(opportunity.tags),
                    decision_snapshot=snapshot,
                    assessment=assessment,
                    recruitment_value=recruitment_value,
                )
            )

        return targets

    def _decision_snapshot(
        self,
        opportunity: OpportunityAssessment,
        indicators: list[StrategicIndicator],
        facts: list[IntelligenceFact],
    ) -> DecisionSnapshot:

        health = self._indicator(
            indicators,
            "Structural Health",
        )

        talent = self._indicator(
            indicators,
            "Talent Value",
        )

        recruitability = self._indicator(
            indicators,
            "Recruitability",
        )

        reasons = list(
            opportunity.evidence,
        )

        if not reasons:
            reasons.extend(
                fact.title
                for fact in facts[:5]
            )

        return DecisionSnapshot(
            status=WatchStatus.NEW,
            priority=opportunity.priority.value,
            confidence=opportunity.confidence,
            health=health,
            talent=talent,
            recruitability=recruitability,
            opportunity=opportunity.score,
            summary=opportunity.description,
            reasons=reasons,
        )

    @staticmethod
    def _indicator(
        indicators: list[StrategicIndicator],
        title: str,
    ) -> float:

        for indicator in indicators:
            if indicator.title == title:
                return float(indicator.value)

        return 0.0

    @staticmethod
    def _priority(
        priority: OpportunityPriority,
    ) -> WatchPriority:

        if priority == OpportunityPriority.CRITICAL:
            return WatchPriority.IMMEDIATE

        if priority == OpportunityPriority.HIGH:
            return WatchPriority.HIGH

        if priority == OpportunityPriority.MEDIUM:
            return WatchPriority.MEDIUM

        return WatchPriority.LOW