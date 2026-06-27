"""
Sentinel
Entity Matcher
"""

from __future__ import annotations

from analytics.matching.models import (
    MatchCandidate,
    MatchDecision,
    MatchResult,
)


class EntityMatcher:
    """
    Matches entities across snapshots.

    v1 logic is intentionally conservative:
    identical normalized names are treated as strong matches.
    Power proximity can increase confidence, but never replaces name matching.
    """

    def match(
        self,
        baseline: MatchCandidate,
        current: MatchCandidate,
    ) -> MatchResult:
        reasons: list[str] = []

        confidence = 0.0

        if self._normalize(baseline.name) == self._normalize(current.name):
            confidence += 80.0
            reasons.append("Normalized names match.")

        if baseline.power is not None and current.power is not None:
            power_confidence = self._power_similarity(
                baseline.power,
                current.power,
            )

            confidence += power_confidence
            reasons.append(
                f"Power similarity contributed {power_confidence:.1f} confidence."
            )

        confidence = min(confidence, 100.0)

        if confidence >= 90:
            decision = MatchDecision.MATCH
        elif confidence >= 70:
            decision = MatchDecision.POSSIBLE_MATCH
        else:
            decision = MatchDecision.NO_MATCH

        return MatchResult(
            baseline=baseline,
            current=current,
            confidence=round(confidence, 2),
            decision=decision,
            reasons=reasons,
        )

    @staticmethod
    def _normalize(
        value: str,
    ) -> str:
        return value.strip().casefold()

    @staticmethod
    def _power_similarity(
        baseline_power: float,
        current_power: float,
    ) -> float:
        if baseline_power <= 0 or current_power <= 0:
            return 0.0

        delta = abs(current_power - baseline_power) / baseline_power

        if delta <= 0.01:
            return 20.0

        if delta <= 0.03:
            return 15.0

        if delta <= 0.07:
            return 10.0

        if delta <= 0.12:
            return 5.0

        return 0.0