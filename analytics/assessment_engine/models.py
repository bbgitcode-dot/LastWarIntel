"""Sentinel Assessment Engine models.

The assessment engine converts deterministic reasoning output into immutable
strategic assessments. Assessments describe situations. They do not prioritize,
recommend actions, mutate state, or perform calculations after creation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from analytics.intelligence.indicators import StrategicIndicator
from analytics.reasoning.models import (
    FactEntityType,
    FactSeverity,
    IntelligenceFact,
    ReasoningHypothesis,
)


class AssessmentType(Enum):
    """Reusable strategic situation types."""

    RECRUITMENT_WINDOW = "Recruitment Window"
    ALLIANCE_COLLAPSE_RISK = "Alliance Collapse Risk"
    STRATEGIC_STRENGTH_INCREASE = "Strategic Strength Increase"
    LEADERSHIP_RISK = "Leadership Risk"
    WHALE_MIGRATION = "Whale Migration"
    HIDDEN_OPPORTUNITY = "Hidden Opportunity"
    UNKNOWN = "Unknown"


@dataclass(slots=True, frozen=True)
class AssessmentTarget:
    """Entity being assessed.

    The target is intentionally separate from evidence. Evidence explains why an
    assessment exists; the target defines who or what the assessment is about.
    """

    entity_type: FactEntityType = FactEntityType.UNKNOWN
    entity_id: str = ""
    display_name: str = ""

    @property
    def label(self) -> str:
        if self.display_name:
            return self.display_name
        if self.entity_id:
            return self.entity_id
        return self.entity_type.value


@dataclass(slots=True, frozen=True)
class EvidenceBundle:
    """Grouped evidence supporting one assessment.

    Evidence bundles are the bridge between objective facts, indicators,
    reasoning hypotheses and the resulting strategic situation.
    """

    title: str
    summary: str
    confidence: float
    facts: tuple[IntelligenceFact, ...] = field(default_factory=tuple)
    indicators: tuple[StrategicIndicator, ...] = field(default_factory=tuple)
    hypotheses: tuple[ReasoningHypothesis, ...] = field(default_factory=tuple)

    @property
    def fact_count(self) -> int:
        return len(self.facts)

    @property
    def indicator_count(self) -> int:
        return len(self.indicators)

    @property
    def hypothesis_count(self) -> int:
        return len(self.hypotheses)

    @property
    def source_ids(self) -> tuple[str, ...]:
        return tuple(fact.id for fact in self.facts)


@dataclass(slots=True, frozen=True)
class StrategicAssessment:
    """Immutable strategic situation produced by the Assessment Engine."""

    assessment_type: AssessmentType
    target: AssessmentTarget
    title: str
    summary: str
    confidence: float
    severity: FactSeverity
    evidence: tuple[EvidenceBundle, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)

    @property
    def fact_count(self) -> int:
        return sum(bundle.fact_count for bundle in self.evidence)

    @property
    def indicator_count(self) -> int:
        return sum(bundle.indicator_count for bundle in self.evidence)

    @property
    def hypothesis_count(self) -> int:
        return sum(bundle.hypothesis_count for bundle in self.evidence)

    @property
    def explanation(self) -> str:
        if not self.evidence:
            return self.summary

        strongest = max(self.evidence, key=lambda item: item.confidence)
        return f"{self.summary} Supporting evidence: {strongest.summary}"


@dataclass(slots=True, frozen=True)
class AssessmentContext:
    """Input object for assessment evaluation."""

    facts: tuple[IntelligenceFact, ...] = field(default_factory=tuple)
    indicators: tuple[StrategicIndicator, ...] = field(default_factory=tuple)
    hypotheses: tuple[ReasoningHypothesis, ...] = field(default_factory=tuple)
    target: AssessmentTarget | None = None

    @classmethod
    def from_lists(
        cls,
        *,
        facts: list[IntelligenceFact] | None = None,
        indicators: list[StrategicIndicator] | None = None,
        hypotheses: list[ReasoningHypothesis] | None = None,
        target: AssessmentTarget | None = None,
    ) -> "AssessmentContext":
        return cls(
            facts=tuple(facts or []),
            indicators=tuple(indicators or []),
            hypotheses=tuple(hypotheses or []),
            target=target,
        )


@dataclass(slots=True, frozen=True)
class AssessmentResult:
    """Complete output of one Assessment Engine run."""

    assessments: tuple[StrategicAssessment, ...] = field(default_factory=tuple)

    @property
    def count(self) -> int:
        return len(self.assessments)

    @property
    def strongest(self) -> StrategicAssessment | None:
        if not self.assessments:
            return None

        return max(
            self.assessments,
            key=lambda assessment: (
                _severity_value(assessment.severity),
                assessment.confidence,
            ),
        )


def _severity_value(severity: FactSeverity) -> int:
    mapping = {
        FactSeverity.LOW: 1,
        FactSeverity.MEDIUM: 2,
        FactSeverity.HIGH: 3,
        FactSeverity.CRITICAL: 4,
    }
    return mapping[severity]
