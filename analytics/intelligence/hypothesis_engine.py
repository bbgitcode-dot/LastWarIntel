"""
LastWarIntel
Hypothesis Engine
Version: 1.0

Generates strategic hypotheses from an EntityReport.
"""

from __future__ import annotations

from analytics.application.models import EntityReport
from analytics.intelligence.models import (
    Hypothesis,
    HypothesisCategory,
    IntelligencePriority,
)


class HypothesisEngine:
    """
    Generates strategic hypotheses based on multiple intelligence sources.
    """

    def analyze(
        self,
        report: EntityReport,
    ) -> list[Hypothesis]:

        hypotheses: list[Hypothesis] = []

        hypotheses.extend(self._detect_collapse(report))
        hypotheses.extend(self._detect_recovery(report))

        hypotheses.sort(
            key=lambda h: h.confidence,
            reverse=True,
        )

        return hypotheses

    def _detect_collapse(
        self,
        report: EntityReport,
    ) -> list[Hypothesis]:

        if (
            report.timeline is None
            or report.health is None
        ):
            return []

        trend = report.timeline.assessment.trend.value
        health = report.health.health.status

        if (
            trend == "Collapsing"
            and health == "Critical"
        ):

            evidence = []

            evidence.extend(report.timeline.assessment.evidence)

            if report.events:
                evidence.extend(
                    event.summary
                    for event in report.events.high_events
                )

            return [
                Hypothesis(
                    title="Alliance is likely disbanding",
                    summary=(
                        "Multiple independent indicators suggest "
                        "that this alliance is collapsing."
                    ),
                    confidence=96,
                    priority=IntelligencePriority.CRITICAL,
                    category=HypothesisCategory.COLLAPSE,
                    evidence=evidence,
                )
            ]

        return []

    def _detect_recovery(
        self,
        report: EntityReport,
    ) -> list[Hypothesis]:

        if (
            report.timeline is None
            or report.health is None
        ):
            return []

        trend = report.timeline.assessment.trend.value
        status = report.health.health.status

        if (
            trend == "Recovering"
            and status == "Healthy"
        ):

            return [
                Hypothesis(
                    title="Alliance successfully recovered",
                    summary=(
                        "The alliance appears to have recovered after "
                        "an earlier setback."
                    ),
                    confidence=90,
                    priority=IntelligencePriority.MEDIUM,
                    category=HypothesisCategory.RECOVERY,
                    evidence=list(report.timeline.assessment.evidence),
                )
            ]

        return []