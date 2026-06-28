"""Recruitment assessment rules.

Purpose
-------
Detect recruitment opportunities caused by instability, high recruitability or
explicit recruitment-window reasoning hypotheses.

Inputs
------
AssessmentContext containing any combination of:

* Intelligence facts tagged with ``decline``
* Strategic indicators named ``Recruitability`` or ``Talent Value``
* Reasoning hypotheses of type ``RECRUITMENT_WINDOW``

Produces
--------
A single immutable ``StrategicAssessment`` of type ``RECRUITMENT_WINDOW`` when
available evidence is strong enough.

Non-responsibilities
--------------------
This rule does not calculate Recruitment Value, create recommendations, persist
results, contact players, or decide whether leadership should act. It only
answers one question: does a recruitment window exist?
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
from analytics.recruitment.assessment_models import (
    DECLINE_FACT_TAG,
    RECRUITABILITY_INDICATOR_TITLE,
    RECRUITMENT_WINDOW_TAGS,
    RECRUITMENT_WINDOW_TITLE,
    TALENT_VALUE_INDICATOR_TITLE,
)
from analytics.reasoning.models import (
    FactEntityType,
    FactSeverity,
    HypothesisType,
    IntelligenceFact,
    ReasoningHypothesis,
)


@dataclass(slots=True, frozen=True)
class RecruitmentWindowRule:
    """Detect a recruitment window from facts, indicators and reasoning.

    The rule intentionally combines several independent signals. A single weak
    signal should not create an assessment. Multiple supporting signals increase
    confidence and produce explainable evidence.
    """

    name: str = "recruitment_window"
    priority: int = 100
    minimum_score: float = 45.0

    def evaluate(self, context: AssessmentContext) -> StrategicAssessment | None:
        hypothesis = _hypothesis_by_type(
            context,
            HypothesisType.RECRUITMENT_WINDOW,
        )
        recruitability = _indicator_by_title(context, RECRUITABILITY_INDICATOR_TITLE)
        talent = _indicator_by_title(context, TALENT_VALUE_INDICATOR_TITLE)
        decline_facts = _facts_by_tag(context, DECLINE_FACT_TAG)

        score = 0.0
        if hypothesis is not None:
            score += hypothesis.confidence * 0.55
        if recruitability is not None:
            score += recruitability.value * 0.25
        if talent is not None:
            score += talent.value * 0.15
        score += min(len(decline_facts) * 5, 15)

        if score < self.minimum_score:
            return None

        confidence = round(min(score, 96), 2)
        evidence = EvidenceBundle(
            title="Recruitment opportunity evidence",
            summary=_build_evidence_summary(
                hypothesis=hypothesis,
                decline_fact_count=len(decline_facts),
                has_recruitability=recruitability is not None,
                has_talent=talent is not None,
            ),
            confidence=confidence,
            facts=tuple(decline_facts),
            indicators=tuple(item for item in (recruitability, talent) if item is not None),
            hypotheses=tuple(item for item in (hypothesis,) if item is not None),
        )

        return StrategicAssessment(
            assessment_type=AssessmentType.RECRUITMENT_WINDOW,
            target=_resolve_target(context),
            title=RECRUITMENT_WINDOW_TITLE,
            summary="Current signals indicate a possible recruitment window.",
            confidence=confidence,
            severity=_severity_from_score(score),
            evidence=(evidence,),
            tags=RECRUITMENT_WINDOW_TAGS,
            metadata={
                "rule": self.name,
                "score": round(score, 2),
                "minimum_score": self.minimum_score,
            },
        )


def _build_evidence_summary(
    *,
    hypothesis: ReasoningHypothesis | None,
    decline_fact_count: int,
    has_recruitability: bool,
    has_talent: bool,
) -> str:
    parts: list[str] = []
    if hypothesis is not None:
        parts.append("reasoning already suggests a recruitment window")
    if has_recruitability:
        parts.append("recruitability is available")
    if has_talent:
        parts.append("talent value supports the opportunity")
    if decline_fact_count:
        parts.append(f"{decline_fact_count} decline signal(s) are present")

    if not parts:
        return "Recruitment evidence is present."
    return "Recruitment window supported because " + ", ".join(parts) + "."


def _hypothesis_by_type(
    context: AssessmentContext,
    hypothesis_type: HypothesisType,
) -> ReasoningHypothesis | None:
    for hypothesis in context.hypotheses:
        if hypothesis.hypothesis_type == hypothesis_type:
            return hypothesis
    return None


def _indicator_by_title(context: AssessmentContext, title: str):
    for indicator in context.indicators:
        if indicator.title == title:
            return indicator
    return None


def _facts_by_tag(context: AssessmentContext, tag: str) -> list[IntelligenceFact]:
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


__all__ = ["RecruitmentWindowRule"]
