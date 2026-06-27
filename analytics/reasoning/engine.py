"""
Sentinel
Rule-Based Reasoning Engine
"""

from __future__ import annotations

from analytics.reasoning.models import (
    Assessment,
    FactSeverity,
    HypothesisType,
    IntelligenceFact,
    ReasoningContext,
    ReasoningHypothesis,
    ReasoningResult,
    Recommendation,
)


class RuleBasedReasoningEngine:
    """
    Deterministic reasoning engine.

    This engine derives strategic hypotheses from
    facts and indicators.
    """

    def reason(
        self,
        facts: list[IntelligenceFact],
    ) -> ReasoningResult:
        """
        Backward-compatible fact-only reasoning.
        """

        return self.reason_context(
            ReasoningContext(
                facts=facts,
            )
        )

    def reason_context(
        self,
        context: ReasoningContext,
    ) -> ReasoningResult:

        hypotheses = self._build_hypotheses(
            context,
        )

        if hypotheses:
            strongest = max(
                hypotheses,
                key=lambda hypothesis: (
                    self._severity_value(hypothesis.severity),
                    hypothesis.confidence,
                ),
            )

            assessment = Assessment(
                title=strongest.title,
                summary=strongest.description,
            )

            recommendation = Recommendation(
                title=self._recommendation_title(
                    strongest,
                ),
                description=self._recommendation_description(
                    strongest,
                ),
                priority=strongest.severity,
            )

            return ReasoningResult(
                facts=context.facts,
                indicators=context.indicators,
                hypotheses=hypotheses,
                assessment=assessment,
                recommendation=recommendation,
            )

        if not context.facts:
            return ReasoningResult(
                indicators=context.indicators,
            )

        highest = max(
            context.facts,
            key=lambda fact: self._severity_value(
                fact.severity,
            ),
        )

        return ReasoningResult(
            facts=context.facts,
            indicators=context.indicators,
            assessment=Assessment(
                title=highest.title,
                summary=highest.description,
            ),
            recommendation=Recommendation(
                title="Review Situation",
                description=(
                    "Review the supporting evidence and "
                    "consider strategic action."
                ),
                priority=highest.severity,
            ),
        )

    def _build_hypotheses(
        self,
        context: ReasoningContext,
    ) -> list[ReasoningHypothesis]:

        hypotheses: list[ReasoningHypothesis] = []

        collapse = self._collapse_risk(
            context,
        )

        if collapse is not None:
            hypotheses.append(
                collapse,
            )

        recruitment = self._recruitment_window(
            context,
        )

        if recruitment is not None:
            hypotheses.append(
                recruitment,
            )

        strength = self._strength_increase(
            context,
        )

        if strength is not None:
            hypotheses.append(
                strength,
            )

        return hypotheses

    def _collapse_risk(
        self,
        context: ReasoningContext,
    ) -> ReasoningHypothesis | None:

        decline_facts = self._facts_by_tag(
            context.facts,
            "decline",
        )

        health = self._indicator_value(
            context,
            "Structural Health",
        )

        whale_facts = self._facts_by_tag(
            context.facts,
            "whale",
        )

        evidence: list[str] = []

        evidence.extend(
            fact.description
            for fact in decline_facts[:3]
        )

        evidence.extend(
            fact.description
            for fact in whale_facts[:3]
        )

        if health:
            evidence.append(
                f"Structural Health indicator: {health:.0f}."
            )

        score = 0.0

        score += len(decline_facts) * 25
        score += len(whale_facts) * 15

        if health and health <= 60:
            score += 30

        if score < 35:
            return None

        severity = self._severity_from_score(
            score,
        )

        return ReasoningHypothesis(
            hypothesis_type=HypothesisType.COLLAPSE_RISK,
            title="Alliance Collapse Risk",
            description=(
                "The alliance shows signs of structural weakening."
            ),
            confidence=min(
                60 + score * 0.4,
                95,
            ),
            severity=severity,
            evidence=evidence,
            tags=[
                "collapse",
                "risk",
                "health",
            ],
        )

    def _recruitment_window(
        self,
        context: ReasoningContext,
    ) -> ReasoningHypothesis | None:

        recruitability = self._indicator_value(
            context,
            "Recruitability",
        )

        talent = self._indicator_value(
            context,
            "Talent Value",
        )

        decline_facts = self._facts_by_tag(
            context.facts,
            "decline",
        )

        score = (
            recruitability * 0.45
            + talent * 0.35
            + len(decline_facts) * 12
        )

        if score < 45:
            return None

        evidence = [
            f"Recruitability indicator: {recruitability:.0f}.",
            f"Talent Value indicator: {talent:.0f}.",
        ]

        evidence.extend(
            fact.description
            for fact in decline_facts[:3]
        )

        return ReasoningHypothesis(
            hypothesis_type=HypothesisType.RECRUITMENT_WINDOW,
            title="Recruitment Window",
            description=(
                "Current signals suggest a possible recruitment window."
            ),
            confidence=min(
                65 + score * 0.3,
                96,
            ),
            severity=self._severity_from_score(
                score,
            ),
            evidence=evidence,
            tags=[
                "recruitment",
                "opportunity",
            ],
        )

    def _strength_increase(
        self,
        context: ReasoningContext,
    ) -> ReasoningHypothesis | None:

        growth_facts = [
            fact
            for fact in self._facts_by_tag(
                context.facts,
                "growth",
            )
            if any(
                tag.casefold() == "growth"
                for tag in fact.tags
            )
            and not any(
                tag.casefold() == "decline"
                for tag in fact.tags
            )
        ]

        whale_balance = self._indicator_value(
            context,
            "Whale Balance",
        )

        score = len(growth_facts) * 20

        if whale_balance > 0:
            score += whale_balance * 20

        if score < 35:
            return None

        evidence = [
            fact.description
            for fact in growth_facts[:3]
        ]

        if whale_balance:
            evidence.append(
                f"Whale Balance indicator: {whale_balance:.0f}."
            )

        return ReasoningHypothesis(
            hypothesis_type=HypothesisType.STRENGTH_INCREASE,
            title="Strategic Strength Increase",
            description=(
                "Current signals suggest increasing strategic strength."
            ),
            confidence=min(
                60 + score * 0.35,
                95,
            ),
            severity=self._severity_from_score(
                score,
            ),
            evidence=evidence,
            tags=[
                "growth",
                "strength",
            ],
        )

    @staticmethod
    def _facts_by_tag(
        facts: list[IntelligenceFact],
        tag: str,
    ) -> list[IntelligenceFact]:

        normalized = tag.casefold()

        return [
            fact
            for fact in facts
            if any(
                item.casefold() == normalized
                for item in fact.tags
            )
        ]

    @staticmethod
    def _indicator_value(
        context: ReasoningContext,
        title: str,
    ) -> float:

        for indicator in context.indicators:
            if indicator.title == title:
                return float(
                    indicator.value,
                )

        return 0.0

    @staticmethod
    def _severity_from_score(
        score: float,
    ) -> FactSeverity:

        if score >= 85:
            return FactSeverity.CRITICAL

        if score >= 65:
            return FactSeverity.HIGH

        if score >= 35:
            return FactSeverity.MEDIUM

        return FactSeverity.LOW

    @staticmethod
    def _severity_value(
        severity: FactSeverity,
    ) -> int:

        mapping = {
            FactSeverity.LOW: 1,
            FactSeverity.MEDIUM: 2,
            FactSeverity.HIGH: 3,
            FactSeverity.CRITICAL: 4,
        }

        return mapping[severity]

    @staticmethod
    def _recommendation_title(
        hypothesis: ReasoningHypothesis,
    ) -> str:

        if hypothesis.hypothesis_type == HypothesisType.RECRUITMENT_WINDOW:
            return "Prepare Recruitment Outreach"

        if hypothesis.hypothesis_type == HypothesisType.COLLAPSE_RISK:
            return "Monitor Alliance Stability"

        if hypothesis.hypothesis_type == HypothesisType.STRENGTH_INCREASE:
            return "Verify Strength Increase"

        return "Review Situation"

    @staticmethod
    def _recommendation_description(
        hypothesis: ReasoningHypothesis,
    ) -> str:

        if hypothesis.hypothesis_type == HypothesisType.RECRUITMENT_WINDOW:
            return (
                "Review target contacts and prepare diplomatic outreach."
            )

        if hypothesis.hypothesis_type == HypothesisType.COLLAPSE_RISK:
            return (
                "Track additional movement and verify whether instability continues."
            )

        if hypothesis.hypothesis_type == HypothesisType.STRENGTH_INCREASE:
            return (
                "Verify whether the strength increase is concentrated or sustainable."
            )

        return (
            "Review the supporting evidence and consider strategic action."
        )