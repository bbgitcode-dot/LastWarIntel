"""Default Sentinel assessment rules.

This module exposes the default assessment rule set used by the generic
Assessment Engine. Domain-specific rules should live in their domain packages.
The engine itself remains domain-neutral.
"""

from __future__ import annotations

from dataclasses import dataclass

from analytics.assessment_engine.base_rule import AssessmentRule
from analytics.assessment_engine.models import (
    AssessmentContext,
    AssessmentTarget,
    AssessmentType,
    EvidenceBundle,
    StrategicAssessment,
)
from analytics.intelligence.indicators import StrategicIndicator
from analytics.reasoning.models import (
    FactEntityType,
    FactSeverity,
    HypothesisType,
    IntelligenceFact,
    ReasoningHypothesis,
)
from analytics.recruitment.assessment_rules import RecruitmentWindowRule


from analytics.capabilities.alliance_stability.rules.alliance_collapse_rule import (
    AllianceCollapseRiskRule,
)


@dataclass(slots=True, frozen=True)
class StrategicStrengthIncreaseRule:
    """Detects meaningful strategic strength increase."""

    name: str = "strategic_strength_increase"
    priority: int = 300

    def evaluate(self, context: AssessmentContext) -> StrategicAssessment | None:
        hypothesis = _hypothesis_by_type(
            context,
            HypothesisType.STRENGTH_INCREASE,
        )
        growth_facts = _facts_by_tag(context, "growth")
        whale_balance = _indicator_by_title(context, "Whale Balance")

        score = 0.0
        if hypothesis is not None:
            score += hypothesis.confidence * 0.65
        score += min(len(growth_facts) * 12, 30)
        if whale_balance is not None and whale_balance.value > 0:
            score += min(whale_balance.value * 10, 20)

        if score < 45:
            return None

        evidence = EvidenceBundle(
            title="Strength increase evidence",
            summary="Growth facts and whale balance support a strategic strength increase.",
            confidence=round(min(score, 95), 2),
            facts=tuple(growth_facts),
            indicators=tuple(item for item in (whale_balance,) if item is not None),
            hypotheses=tuple(item for item in (hypothesis,) if item is not None),
        )

        return StrategicAssessment(
            assessment_type=AssessmentType.STRATEGIC_STRENGTH_INCREASE,
            target=_resolve_target(context),
            title="Strategic Strength Increase",
            summary="Current signals indicate increasing strategic strength.",
            confidence=evidence.confidence,
            severity=_severity_from_score(score),
            evidence=(evidence,),
            tags=("growth", "strength"),
        )


def default_assessment_rules() -> list[AssessmentRule]:
    """Return the default deterministic assessment rule set."""

    return [
        RecruitmentWindowRule(),
        AllianceCollapseRiskRule(),
        StrategicStrengthIncreaseRule(),
    ]


def _hypothesis_by_type(
    context: AssessmentContext,
    hypothesis_type: HypothesisType,
) -> ReasoningHypothesis | None:
    for hypothesis in context.hypotheses:
        if hypothesis.hypothesis_type == hypothesis_type:
            return hypothesis
    return None


def _indicator_by_title(
    context: AssessmentContext,
    title: str,
) -> StrategicIndicator | None:
    for indicator in context.indicators:
        if indicator.title == title:
            return indicator
    return None


def _facts_by_tag(
    context: AssessmentContext,
    tag: str,
) -> list[IntelligenceFact]:
    normalized = tag.casefold()
    return [
        fact
        for fact in context.facts
        if any(item.casefold() == normalized for item in fact.tags)
    ]


def _resolve_target(context: AssessmentContext) -> AssessmentTarget:
    if context.target is not None:
        return context.target

    for fact in context.facts:
        if fact.entity_type != FactEntityType.UNKNOWN or fact.entity_id:
            return AssessmentTarget(
                entity_type=fact.entity_type,
                entity_id=fact.entity_id,
                display_name=fact.entity_id,
            )

    return AssessmentTarget()


def _severity_from_score(score: float) -> FactSeverity:
    if score >= 85:
        return FactSeverity.CRITICAL
    if score >= 65:
        return FactSeverity.HIGH
    if score >= 35:
        return FactSeverity.MEDIUM
    return FactSeverity.LOW
