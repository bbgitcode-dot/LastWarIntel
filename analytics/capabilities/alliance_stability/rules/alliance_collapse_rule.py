"""Alliance Collapse assessment rule.

Purpose
-------
Detect alliance collapse risk from explainable instability evidence.

Inputs
------
AssessmentContext containing any combination of:

* Intelligence facts tagged with collapse support tags such as ``decline``,
  ``whale``, ``officer``, ``leadership``, ``power_loss`` or ``member_loss``
* Strategic indicators named ``Structural Health``, ``Whale Density`` or
  ``Activity``
* Reasoning hypotheses of type ``COLLAPSE_RISK`` or
  ``STRUCTURAL_INSTABILITY``

Produces
--------
A single immutable ``StrategicAssessment`` of type
``ALLIANCE_COLLAPSE_RISK`` when evidence is strong enough.

Non-responsibilities
--------------------
This rule does not calculate values, produce recommendations, persist data,
load repositories, mutate context or perform presentation work. It only answers
one strategic question: does the available evidence indicate alliance collapse
risk?
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
from analytics.capabilities.alliance_stability.models.assessments import (
    ACTIVITY_INDICATOR,
    ALLIANCE_COLLAPSE_RULE_NAME,
    ALLIANCE_COLLAPSE_TAGS,
    ALLIANCE_COLLAPSE_TITLE,
    COLLAPSE_SUPPORT_TAGS,
    LEADERSHIP_FACT_TAG,
    OFFICER_FACT_TAG,
    STRUCTURAL_HEALTH_INDICATOR,
    WHALE_DENSITY_INDICATOR,
    WHALE_FACT_TAG,
)
from analytics.intelligence.indicators import StrategicIndicator
from analytics.reasoning.models import (
    FactEntityType,
    FactSeverity,
    HypothesisType,
    IntelligenceFact,
    ReasoningHypothesis,
)


@dataclass(slots=True, frozen=True)
class AllianceCollapseRule:
    """Detect structural alliance collapse risk.

    The rule requires multiple independent instability signals. A single weak
    fact should not create a collapse assessment. Confidence increases when
    several evidence categories agree: reasoning hypotheses, low structural
    health, whale loss, leadership/officer loss and broader decline signals.
    """

    name: str = ALLIANCE_COLLAPSE_RULE_NAME
    priority: int = 200
    minimum_score: float = 60.0

    def evaluate(self, context: AssessmentContext) -> StrategicAssessment | None:
        collapse_hypothesis = _hypothesis_by_type(
            context,
            HypothesisType.COLLAPSE_RISK,
        )
        instability_hypothesis = _hypothesis_by_type(
            context,
            HypothesisType.STRUCTURAL_INSTABILITY,
        )
        structural_health = _indicator_by_title(context, STRUCTURAL_HEALTH_INDICATOR)
        whale_density = _indicator_by_title(context, WHALE_DENSITY_INDICATOR)
        activity = _indicator_by_title(context, ACTIVITY_INDICATOR)

        support_facts = _facts_by_any_tag(context, COLLAPSE_SUPPORT_TAGS)
        whale_facts = _facts_by_tag(context, WHALE_FACT_TAG)
        leadership_facts = _facts_by_any_tag(
            context,
            (OFFICER_FACT_TAG, LEADERSHIP_FACT_TAG),
        )

        score = _calculate_score(
            collapse_hypothesis=collapse_hypothesis,
            instability_hypothesis=instability_hypothesis,
            structural_health=structural_health,
            whale_density=whale_density,
            activity=activity,
            support_facts=support_facts,
            whale_facts=whale_facts,
            leadership_facts=leadership_facts,
        )

        if score < self.minimum_score:
            return None

        confidence = round(min(score, 97.0), 2)
        evidence = EvidenceBundle(
            title="Alliance collapse evidence",
            summary=_build_evidence_summary(
                collapse_hypothesis=collapse_hypothesis,
                instability_hypothesis=instability_hypothesis,
                structural_health=structural_health,
                whale_density=whale_density,
                activity=activity,
                support_fact_count=len(support_facts),
                whale_fact_count=len(whale_facts),
                leadership_fact_count=len(leadership_facts),
            ),
            confidence=confidence,
            facts=tuple(support_facts),
            indicators=tuple(
                indicator
                for indicator in (structural_health, whale_density, activity)
                if indicator is not None
            ),
            hypotheses=tuple(
                hypothesis
                for hypothesis in (collapse_hypothesis, instability_hypothesis)
                if hypothesis is not None
            ),
        )

        return StrategicAssessment(
            assessment_type=AssessmentType.ALLIANCE_COLLAPSE_RISK,
            target=_resolve_target(context),
            title=ALLIANCE_COLLAPSE_TITLE,
            summary="Current signals indicate meaningful alliance collapse risk.",
            confidence=confidence,
            severity=_severity_from_score(score),
            evidence=(evidence,),
            tags=ALLIANCE_COLLAPSE_TAGS,
            metadata={
                "rule": self.name,
                "score": round(score, 2),
                "minimum_score": self.minimum_score,
                "support_facts": len(support_facts),
                "whale_facts": len(whale_facts),
                "leadership_facts": len(leadership_facts),
            },
        )


def _calculate_score(
    *,
    collapse_hypothesis: ReasoningHypothesis | None,
    instability_hypothesis: ReasoningHypothesis | None,
    structural_health: StrategicIndicator | None,
    whale_density: StrategicIndicator | None,
    activity: StrategicIndicator | None,
    support_facts: list[IntelligenceFact],
    whale_facts: list[IntelligenceFact],
    leadership_facts: list[IntelligenceFact],
) -> float:
    score = 0.0

    if collapse_hypothesis is not None:
        score += collapse_hypothesis.confidence * 0.48
    if instability_hypothesis is not None:
        score += instability_hypothesis.confidence * 0.28

    if structural_health is not None:
        score += _low_indicator_score(
            value=structural_health.value,
            threshold=65.0,
            weight=0.70,
            maximum=35.0,
        )
    if whale_density is not None:
        score += _low_indicator_score(
            value=whale_density.value,
            threshold=45.0,
            weight=0.45,
            maximum=18.0,
        )
    if activity is not None:
        score += _low_indicator_score(
            value=activity.value,
            threshold=50.0,
            weight=0.35,
            maximum=15.0,
        )

    score += min(len(support_facts) * 7.0, 28.0)
    score += min(len(whale_facts) * 9.0, 24.0)
    score += min(len(leadership_facts) * 10.0, 22.0)

    return score


def _low_indicator_score(
    *,
    value: float,
    threshold: float,
    weight: float,
    maximum: float,
) -> float:
    if value >= threshold:
        return 0.0
    return min((threshold - value) * weight, maximum)


def _build_evidence_summary(
    *,
    collapse_hypothesis: ReasoningHypothesis | None,
    instability_hypothesis: ReasoningHypothesis | None,
    structural_health: StrategicIndicator | None,
    whale_density: StrategicIndicator | None,
    activity: StrategicIndicator | None,
    support_fact_count: int,
    whale_fact_count: int,
    leadership_fact_count: int,
) -> str:
    parts: list[str] = []

    if collapse_hypothesis is not None:
        parts.append("reasoning already indicates collapse risk")
    if instability_hypothesis is not None:
        parts.append("reasoning indicates structural instability")
    if structural_health is not None and structural_health.value < 65:
        parts.append(f"structural health is low ({structural_health.value:g})")
    if whale_density is not None and whale_density.value < 45:
        parts.append(f"whale density is weakened ({whale_density.value:g})")
    if activity is not None and activity.value < 50:
        parts.append(f"activity is reduced ({activity.value:g})")
    if support_fact_count:
        parts.append(f"{support_fact_count} instability fact(s) are present")
    if whale_fact_count:
        parts.append(f"{whale_fact_count} whale-related decline signal(s) are present")
    if leadership_fact_count:
        parts.append(f"{leadership_fact_count} leadership/officer signal(s) are present")

    if not parts:
        return "Alliance collapse evidence is present."
    return "Alliance collapse risk is supported because " + ", ".join(parts) + "."


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


def _facts_by_any_tag(
    context: AssessmentContext,
    tags: tuple[str, ...],
) -> list[IntelligenceFact]:
    normalized = {tag.casefold() for tag in tags}
    return [
        fact
        for fact in context.facts
        if any(item.casefold() in normalized for item in fact.tags)
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
    if score >= 90:
        return FactSeverity.CRITICAL
    if score >= 70:
        return FactSeverity.HIGH
    if score >= 45:
        return FactSeverity.MEDIUM
    return FactSeverity.LOW


AllianceCollapseRiskRule = AllianceCollapseRule

__all__ = ["AllianceCollapseRule", "AllianceCollapseRiskRule"]
