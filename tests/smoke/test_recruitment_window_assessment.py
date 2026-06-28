from dataclasses import FrozenInstanceError

import pytest

from analytics.assessment_engine import AssessmentTarget, AssessmentType
from analytics.assessment_engine.models import AssessmentContext
from analytics.intelligence.indicators import IndicatorLevel, IndicatorScope, StrategicIndicator
from analytics.reasoning.models import (
    FactEntityType,
    FactSeverity,
    HypothesisType,
    IntelligenceFact,
    ReasoningHypothesis,
)
from analytics.recruitment.assessment_facade import RecruitmentAssessmentFacade
from analytics.recruitment.assessment_rules import RecruitmentWindowRule


def _target() -> AssessmentTarget:
    return AssessmentTarget(
        entity_type=FactEntityType.ALLIANCE,
        entity_id="ACEv",
        display_name="ACEv",
    )


def test_recruitment_window_rule_detects_window_from_combined_signals():
    fact = IntelligenceFact(
        source="smoke",
        title="Alliance power declined",
        description="Alliance lost significant power.",
        severity=FactSeverity.HIGH,
        entity_type=FactEntityType.ALLIANCE,
        entity_id="ACEv",
        tags=["decline"],
    )
    recruitability = StrategicIndicator(
        title="Recruitability",
        value=86,
        scope=IndicatorScope.ALLIANCE,
        level=IndicatorLevel.HIGH,
    )
    talent = StrategicIndicator(
        title="Talent Value",
        value=80,
        scope=IndicatorScope.ALLIANCE,
        level=IndicatorLevel.HIGH,
    )
    hypothesis = ReasoningHypothesis(
        hypothesis_type=HypothesisType.RECRUITMENT_WINDOW,
        title="Recruitment Window",
        description="Current signals suggest a recruitment window.",
        confidence=90,
        severity=FactSeverity.HIGH,
        evidence=["High recruitability."],
        tags=["recruitment"],
    )

    result = RecruitmentAssessmentFacade().evaluate_context(
        AssessmentContext.from_lists(
            facts=[fact],
            indicators=[recruitability, talent],
            hypotheses=[hypothesis],
            target=_target(),
        )
    )

    assert result.count == 1
    assessment = result.strongest
    assert assessment is not None
    assert assessment.assessment_type == AssessmentType.RECRUITMENT_WINDOW
    assert assessment.target.entity_id == "ACEv"
    assert assessment.confidence >= 80
    assert assessment.evidence_count == 1
    assert assessment.fact_count == 1
    assert assessment.indicator_count == 2
    assert assessment.hypothesis_count == 1
    assert assessment.metadata["rule"] == "recruitment_window"


def test_recruitment_window_rule_returns_none_without_sufficient_signals():
    context = AssessmentContext.from_lists(target=_target())

    assessment = RecruitmentWindowRule().evaluate(context)

    assert assessment is None


def test_recruitment_window_rule_keeps_assessment_immutable():
    hypothesis = ReasoningHypothesis(
        hypothesis_type=HypothesisType.RECRUITMENT_WINDOW,
        title="Recruitment Window",
        description="Current signals suggest a recruitment window.",
        confidence=95,
        severity=FactSeverity.HIGH,
        evidence=["Recruitment hypothesis."],
        tags=["recruitment"],
    )

    result = RecruitmentAssessmentFacade().evaluate_context(
        AssessmentContext.from_lists(hypotheses=[hypothesis], target=_target())
    )
    assessment = result.strongest

    assert assessment is not None
    with pytest.raises(FrozenInstanceError):
        assessment.summary = "Changed"


def test_recruitment_window_rule_evidence_explains_why_assessment_exists():
    fact = IntelligenceFact(
        source="smoke",
        title="Whale left alliance",
        description="A high-value player left the alliance.",
        severity=FactSeverity.HIGH,
        entity_type=FactEntityType.ALLIANCE,
        entity_id="ACEv",
        tags=["decline"],
    )
    hypothesis = ReasoningHypothesis(
        hypothesis_type=HypothesisType.RECRUITMENT_WINDOW,
        title="Recruitment Window",
        description="Current signals suggest a recruitment window.",
        confidence=80,
        severity=FactSeverity.HIGH,
        evidence=["Whale departure increases recruitability."],
        tags=["recruitment"],
    )

    result = RecruitmentAssessmentFacade().evaluate_context(
        AssessmentContext.from_lists(facts=[fact], hypotheses=[hypothesis], target=_target())
    )

    assessment = result.strongest
    assert assessment is not None
    assert "Supporting evidence" in assessment.explanation
    assert "recruitment window" in assessment.evidence[0].summary.lower()
