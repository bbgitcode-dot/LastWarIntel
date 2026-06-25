"""
LastWarIntel
Situation Analyzer
Version: 1.0

Creates an objective description of the current alliance situation.
"""

from __future__ import annotations

from analytics.application.models import EntityReport
from analytics.situation.models import (
    CurrentSituation,
    SituationFinding,
)


class SituationAnalyzer:
    """
    Creates the current situation from available analytics.
    """

    def analyze(
        self,
        report: EntityReport,
    ) -> CurrentSituation:

        findings: list[SituationFinding] = []

        #
        # Health
        #

        if report.health:

            health = report.health.health

            findings.append(
                SituationFinding(
                    title="Alliance Health",
                    description=(
                        f"Alliance health is {health.status} "
                        f"with {health.risk} risk."
                    ),
                    confidence=80,
                )
            )

        #
        # Timeline
        #

        if report.timeline:

            trend = report.timeline.assessment

            findings.append(
                SituationFinding(
                    title="Timeline Trend",
                    description=trend.summary,
                    confidence=trend.confidence,
                )
            )

        #
        # Events
        #

        if report.events:

            high_events = report.events.high_events

            if high_events:

                findings.append(
                    SituationFinding(
                        title="Critical Events",
                        description=(
                            f"{len(high_events)} high-impact "
                            "event(s) detected."
                        ),
                        confidence=90,
                    )
                )

        #
        # Recruitment
        #

        if report.recruitment:

            target = report.recruitment.target

            if target.priority >= 80:

                findings.append(
                    SituationFinding(
                        title="Recruitment Opportunity",
                        description=(
                            "Current recruitment potential is high."
                        ),
                        confidence=target.confidence,
                    )
                )

        #
        # Summary
        #

        if not findings:

            return CurrentSituation(
                summary="No significant developments detected.",
                findings=[],
                confidence=70,
            )

        summary = findings[0].description

        confidence = (
            sum(f.confidence for f in findings)
            / len(findings)
        )

        return CurrentSituation(
            summary=summary,
            findings=findings,
            confidence=confidence,
        )