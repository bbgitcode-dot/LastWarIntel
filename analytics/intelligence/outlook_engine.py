"""
LastWarIntel
Outlook Engine
Version: 1.0

Generates a strategic outlook from an existing strategic assessment.
"""

from __future__ import annotations

from analytics.intelligence.models import (
    HypothesisCategory,
    IntelligencePriority,
    StrategicAssessment,
    StrategicOpportunity,
    StrategicOutlook,
    StrategicRisk,
)


class OutlookEngine:
    """
    Generates high-level risks, opportunities and an outlook.
    """

    def analyze(
        self,
        assessment: StrategicAssessment,
    ) -> StrategicAssessment:

        risks: list[StrategicRisk] = []
        opportunities: list[StrategicOpportunity] = []

        #
        # Evaluate hypotheses
        #

        for hypothesis in assessment.hypotheses:

            #
            # Collapse
            #

            if hypothesis.category == HypothesisCategory.COLLAPSE:

                risks.append(
                    StrategicRisk(
                        title="Alliance Collapse",
                        summary=(
                            "The alliance is very likely entering a late-stage collapse."
                        ),
                        confidence=hypothesis.confidence,
                        priority=IntelligencePriority.CRITICAL,
                    )
                )

                opportunities.append(
                    StrategicOpportunity(
                        title="Recruitment Window",
                        summary=(
                            "A significant recruitment opportunity currently exists."
                        ),
                        confidence=hypothesis.confidence,
                        priority=IntelligencePriority.HIGH,
                    )
                )

            #
            # Recovery
            #

            elif hypothesis.category == HypothesisCategory.RECOVERY:

                opportunities.append(
                    StrategicOpportunity(
                        title="Alliance Recovery",
                        summary=(
                            "The alliance appears to have stabilized after a difficult period."
                        ),
                        confidence=hypothesis.confidence,
                        priority=IntelligencePriority.MEDIUM,
                    )
                )

        #
        # Overall outlook
        #

        if risks:

            outlook = StrategicOutlook(
                summary=(
                    "The alliance is experiencing significant structural changes. "
                    "Immediate diplomatic action is recommended."
                ),
                confidence=max(r.confidence for r in risks),
            )

        elif opportunities:

            outlook = StrategicOutlook(
                summary=(
                    "The alliance appears stable and continues to develop positively."
                ),
                confidence=max(o.confidence for o in opportunities),
            )

        else:

            outlook = StrategicOutlook(
                summary=(
                    "No significant strategic developments detected."
                ),
                confidence=70,
            )

        return StrategicAssessment(
            server=assessment.server,
            alliance=assessment.alliance,
            hypotheses=assessment.hypotheses,
            recommendations=assessment.recommendations,
            risks=risks,
            opportunities=opportunities,
            outlook=outlook,
        )