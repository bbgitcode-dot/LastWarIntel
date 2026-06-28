from dataclasses import FrozenInstanceError

import pytest

from analytics.assessment_engine import AssessmentEngineFacade, AssessmentTarget, AssessmentType
from analytics.assessment_engine.models import AssessmentContext
from analytics.capabilities.alliance_stability import AllianceCollapseRule
from analytics.intelligence.indicators import IndicatorLevel, IndicatorScope, StrategicIndicator
from analytics.reasoning.models import (
    FactEntityType,
    FactSeverity,
    HypothesisType,
    IntelligenceFact,
    ReasoningHypothesis,
)


def _target() -> AssessmentTarget:
    return AssessmentTarget(
        entity_type=FactEntityType.ALLIANCE,
        entity_id="ACEv",
        display_name="ACEv",
    )


def _fact(title: str, tags: list[str], severity: FactSeverity = FactSeverity.HIGH) -> IntelligenceFact:
    return IntelligenceFact(
        source="test",
        title=title,
        description=title,
        severity=severity,
        confidence=94.0,
        entity_type=FactEntityType.ALLIANCE,
        entity_id="ACEv",
        tags=tags,
    )


def test_alliance_collapse_rule_detects_real_collapse_risk_from_combined_evidence():
    facts = [
        _fact("Whale left alliance", ["whale", "decline"]),
        _fact("Officer left alliance", ["officer", "leadership", "decline"]),
        _fact("Alliance power dropped", ["power_loss", "decline"]),
    ]
    indicators = [
        StrategicIndicator(
            title="Structural Health",
            value=32,
            scope=IndicatorScope.ALLIANCE,
            level=IndicatorLevel.LOW,
            summary="Structural health is low.",
        ),
        StrategicIndicator(
            title="Whale Density",
            value=28,
            scope=IndicatorScope.ALLIANCE,
            level=IndicatorLevel.LOW,
            summary="Whale density is weakened.",
        ),
    ]
    hypotheses = [
        ReasoningHypothesis(
            hypothesis_type=HypothesisType.COLLAPSE_RISK,
            title="Collapse risk",
            description="Multiple instability signals indicate collapse risk.",
            confidence=88,
            severity=FactSeverity.HIGH,
            evidence=["Whale and officer left."],
            tags=["collapse", "risk"],
        )
    ]

    result = AssessmentEngineFacade().evaluate(
        facts=facts,
        indicators=indicators,
        hypotheses=hypotheses,
        target=_target(),
    )

    collapse = [
        assessment
        for assessment in result.assessments
        if assessment.assessment_type == AssessmentType.ALLIANCE_COLLAPSE_RISK
    ]
    assert len(collapse) == 1

    assessment = collapse[0]
    assert assessment.target.entity_id == "ACEv"
    assert assessment.confidence >= 90
    assert assessment.severity in (FactSeverity.HIGH, FactSeverity.CRITICAL)
    assert assessment.evidence_count == 1
    assert assessment.fact_count == 3
    assert assessment.indicator_count == 2
    assert assessment.hypothesis_count == 1
    assert assessment.metadata["rule"] == "alliance_collapse"
    assert "collapse risk" in assessment.evidence[0].summary.lower()
    assert "whale" in assessment.evidence[0].summary.lower()


def test_alliance_collapse_rule_returns_none_without_sufficient_evidence():
    context = AssessmentContext.from_lists(
        facts=[_fact("Minor decline", ["decline"], severity=FactSeverity.LOW)],
        indicators=[
            StrategicIndicator(
                title="Structural Health",
                value=82,
                scope=IndicatorScope.ALLIANCE,
                level=IndicatorLevel.HIGH,
            )
        ],
        target=_target(),
    )

    assessment = AllianceCollapseRule().evaluate(context)

    assert assessment is None


def test_alliance_collapse_rule_can_detect_instability_without_hypothesis():
    facts = [
        _fact("Whale left alliance", ["whale", "decline"]),
        _fact("Officer left alliance", ["officer", "leadership"]),
        _fact("Power loss", ["power_loss", "decline"]),
        _fact("Member loss", ["member_loss", "decline"]),
    ]
    indicators = [
        StrategicIndicator(
            title="Structural Health",
            value=20,
            scope=IndicatorScope.ALLIANCE,
            level=IndicatorLevel.CRITICAL,
        ),
        StrategicIndicator(
            title="Activity",
            value=25,
            scope=IndicatorScope.ALLIANCE,
            level=IndicatorLevel.LOW,
        ),
    ]

    assessment = AllianceCollapseRule().evaluate(
        AssessmentContext.from_lists(facts=facts, indicators=indicators, target=_target())
    )

    assert assessment is not None
    assert assessment.assessment_type == AssessmentType.ALLIANCE_COLLAPSE_RISK
    assert assessment.confidence >= 70
    assert assessment.hypothesis_count == 0
    assert assessment.fact_count == 4


def test_alliance_collapse_assessment_is_immutable():
    hypothesis = ReasoningHypothesis(
        hypothesis_type=HypothesisType.COLLAPSE_RISK,
        title="Collapse risk",
        description="Collapse risk is present.",
        confidence=95,
        severity=FactSeverity.HIGH,
        evidence=["Strong collapse risk."],
        tags=["collapse"],
    )
    health = StrategicIndicator(
        title="Structural Health",
        value=30,
        scope=IndicatorScope.ALLIANCE,
        level=IndicatorLevel.LOW,
    )

    assessment = AllianceCollapseRule().evaluate(
        AssessmentContext.from_lists(
            indicators=[health],
            hypotheses=[hypothesis],
            target=_target(),
        )
    )

    assert assessment is not None
    with pytest.raises(FrozenInstanceError):
        assessment.summary = "Changed"
