"""
Sentinel
Recruitment Value Calculator
"""

from __future__ import annotations

from analytics.talent_intelligence.recruitment_context import (
    RecruitmentContext,
)
from analytics.talent_intelligence.recruitment_value import (
    RecruitmentValue,
    ScoreComponent,
)


class RecruitmentValueCalculator:
    """
    Calculates the overall recruitment attractiveness
    of an alliance.
    """

    TALENT_WEIGHT = 0.40
    STABILITY_WEIGHT = 0.25
    WHALE_WEIGHT = 0.20
    ROSTER_WEIGHT = 0.10
    MOMENTUM_WEIGHT = 0.05

    def calculate(
        self,
        context: RecruitmentContext,
    ) -> RecruitmentValue:

        talent = self._talent(context)
        stability = self._stability(context)
        whale = self._whale(context)
        roster = self._roster(context)
        momentum = self._momentum(context)

        overall = self._overall(
            talent=talent,
            stability=stability,
            whale=whale,
            roster=roster,
            momentum=momentum,
        )

        return RecruitmentValue(
            overall=overall,
            talent=talent,
            stability=stability,
            whale=whale,
            roster=roster,
            momentum=momentum,
        )

    def _talent(
        self,
        context: RecruitmentContext,
    ) -> ScoreComponent:

        score = self._clamp(context.talent_value)

        if score >= 90:
            reason = "Exceptional talent concentration."
        elif score >= 75:
            reason = "Strong recruitment potential."
        elif score >= 50:
            reason = "Average talent pool."
        else:
            reason = "Limited recruitment potential."

        return ScoreComponent(
            score=score,
            confidence=100.0,
            reasons=[reason],
        )

    def _stability(
        self,
        context: RecruitmentContext,
    ) -> ScoreComponent:

        weakness = 100.0 - context.structural_health

        score = self._clamp(
            weakness * context.recruitability / 100.0,
        )

        if score >= 75:
            reason = "Alliance is unstable and highly recruitable."
        elif score >= 50:
            reason = "Alliance offers good recruitment opportunities."
        elif score >= 25:
            reason = "Limited recruitment opportunity."
        else:
            reason = "Alliance appears difficult to recruit from."

        return ScoreComponent(
            score=score,
            confidence=100.0,
            reasons=[reason],
        )

    def _whale(
        self,
        context: RecruitmentContext,
    ) -> ScoreComponent:

        score = self._clamp(
            context.whale_density * 5.0,
        )

        if score >= 90:
            reason = "Exceptional whale opportunity."
        elif score >= 70:
            reason = "Strong whale presence."
        elif score >= 40:
            reason = "Moderate whale presence."
        elif score > 0:
            reason = "Limited whale presence."
        else:
            reason = "No whale opportunity detected."

        return ScoreComponent(
            score=score,
            confidence=100.0,
            reasons=[reason],
        )

    def _roster(
        self,
        context: RecruitmentContext,
    ) -> ScoreComponent:

        score = self._clamp(
            context.recruitable_density * 0.6
            + context.elite_density * 0.4,
        )

        if score >= 85:
            reason = "Roster contains many recruitable and elite players."
        elif score >= 65:
            reason = "Roster has strong recruitment depth."
        elif score >= 40:
            reason = "Roster has moderate recruitment depth."
        elif score > 0:
            reason = "Roster has limited recruitment depth."
        else:
            reason = "No relevant recruitment depth detected."

        return ScoreComponent(
            score=round(score, 1),
            confidence=100.0,
            reasons=[reason],
        )

    def _momentum(
        self,
        context: RecruitmentContext,
    ) -> ScoreComponent:

        return ScoreComponent(
            score=self._clamp(context.momentum),
            confidence=0.0,
            reasons=[],
        )

    def _overall(
        self,
        *,
        talent: ScoreComponent,
        stability: ScoreComponent,
        whale: ScoreComponent,
        roster: ScoreComponent,
        momentum: ScoreComponent,
    ) -> ScoreComponent:

        score = (
            talent.score * self.TALENT_WEIGHT
            + stability.score * self.STABILITY_WEIGHT
            + whale.score * self.WHALE_WEIGHT
            + roster.score * self.ROSTER_WEIGHT
            + momentum.score * self.MOMENTUM_WEIGHT
        )

        reasons = (
            talent.reasons
            + stability.reasons
            + whale.reasons
            + roster.reasons
            + momentum.reasons
        )

        return ScoreComponent(
            score=round(score, 1),
            confidence=100.0,
            reasons=reasons,
        )

    @staticmethod
    def _clamp(
        value: float,
    ) -> float:

        return max(
            0.0,
            min(
                100.0,
                float(value),
            ),
        )