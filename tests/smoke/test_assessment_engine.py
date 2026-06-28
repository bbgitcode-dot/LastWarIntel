from dataclasses import FrozenInstanceError

import pytest

from analytics.assessment_engine import AssessmentEngineFacade, AssessmentTarget, AssessmentType
from analytics.intelligence.indicators import IndicatorLevel, IndicatorScope, StrategicIndicator
from analytics.reasoning.models import (
    FactEntityType,
    FactSeverity,
    HypothesisType,
    IntelligenceFact,
    ReasoningHypothesis,
)


def test_assessment_engine_returns_no_assessment_without_signals():
    result = AssessmentEngineFacade().evaluate()

    assert result.count == 0
    assert result.strongest is None


def test_assessment_engine_detects_recruitment_window():
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
        value=82,
        scope=IndicatorScope.ALLIANCE,
        level=IndicatorLevel.HIGH,
    )
    talent = StrategicIndicator(
        title="Talent Value",
        value=78,
        scope=IndicatorScope.ALLIANCE,
        level=IndicatorLevel.HIGH,
    )
    hypothesis = ReasoningHypothesis(
        hypothesis_type=HypothesisType.RECRUITMENT_WINDOW,
        title="Recruitment Window",
        description="Current signals suggest a possible recruitment window.",
        confidence=88,
        severity=FactSeverity.HIGH,
        evidence=["Recruitability indicator is high."],
        tags=["recruitment", "opportunity"],
    )

    result = AssessmentEngineFacade().evaluate(
        facts=[fact],
        indicators=[recruitability, talent],
        hypotheses=[hypothesis],
        target=AssessmentTarget(
            entity_type=FactEntityType.ALLIANCE,
            entity_id="ACEv",
            display_name="ACEv",
        ),
    )

    assert result.count == 1
    assessment = result.strongest
    assert assessment is not None
    assert assessment.assessment_type == AssessmentType.RECRUITMENT_WINDOW
    assert assessment.target.entity_id == "ACEv"
    assert assessment.evidence_count == 1
    assert assessment.fact_count == 1
    assert assessment.indicator_count == 2
    assert assessment.hypothesis_count == 1
    assert assessment.confidence > 70


def test_assessment_engine_assessments_are_immutable():
    hypothesis = ReasoningHypothesis(
        hypothesis_type=HypothesisType.RECRUITMENT_WINDOW,
        title="Recruitment Window",
        description="Current signals suggest a possible recruitment window.",
        confidence=95,
        severity=FactSeverity.HIGH,
        evidence=["Recruitment hypothesis."],
        tags=["recruitment"],
    )

    result = AssessmentEngineFacade().evaluate(hypotheses=[hypothesis])
    assessment = result.strongest

    assert assessment is not None
    with pytest.raises(FrozenInstanceError):
        assessment.title = "Changed"


def test_assessment_engine_detects_collapse_risk():
    fact = IntelligenceFact(
        source="smoke",
        title="Whale left alliance",
        description="A whale left the alliance.",
        severity=FactSeverity.HIGH,
        entity_type=FactEntityType.ALLIANCE,
        entity_id="ACEv",
        tags=["whale", "decline"],
    )
    health = StrategicIndicator(
        title="Structural Health",
        value=42,
        scope=IndicatorScope.ALLIANCE,
        level=IndicatorLevel.LOW,
    )
    hypothesis = ReasoningHypothesis(
        hypothesis_type=HypothesisType.COLLAPSE_RISK,
        title="Alliance Collapse Risk",
        description="The alliance shows signs of structural weakening.",
        confidence=86,
        severity=FactSeverity.HIGH,
        evidence=["Whale left alliance."],
        tags=["collapse", "risk"],
    )

    result = AssessmentEngineFacade().evaluate(
        facts=[fact],
        indicators=[health],
        hypotheses=[hypothesis],
    )

    assert result.count == 1
    assessment = result.strongest
    assert assessment is not None
    assert assessment.assessment_type == AssessmentType.ALLIANCE_COLLAPSE_RISK
    assert assessment.target.entity_id == "ACEv"
