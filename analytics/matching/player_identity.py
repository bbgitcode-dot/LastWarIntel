"""Player identity matching for structured Total Hero Power snapshots.

This module compares structured THP entries across snapshots and produces
explainable identity scores. It deliberately does not create differences,
facts, recommendations, or recruitment decisions. Its single responsibility is
answering: do these two ranking entries describe the same player?
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Optional

from models.player_ranking import PlayerRankingEntry, PlayerRankingSnapshot


@dataclass(slots=True, frozen=True)
class IdentityScoreBreakdown:
    """Explainable score components for one player identity comparison."""

    name_similarity: float
    power_similarity: float
    alliance_similarity: float
    confidence_similarity: float
    weighted_score: float


@dataclass(slots=True, frozen=True)
class PlayerIdentityMatch:
    """Result of comparing two structured player ranking entries."""

    baseline: PlayerRankingEntry
    current: PlayerRankingEntry
    score: float
    decision: str
    breakdown: IdentityScoreBreakdown
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class PlayerSnapshotMatchResult:
    """Best-effort matching result for two player ranking snapshots."""

    baseline_snapshot: PlayerRankingSnapshot
    current_snapshot: PlayerRankingSnapshot
    matches: list[PlayerIdentityMatch]
    unmatched_baseline: list[PlayerRankingEntry]
    unmatched_current: list[PlayerRankingEntry]


class PlayerIdentityMatcher:
    """Deterministic matcher for OCR-derived player ranking entries.

    Server equality is mandatory. Matching then combines four explainable
    signals:

    * name similarity
    * hero power similarity
    * alliance tag similarity
    * OCR/parser confidence
    """

    MATCH_THRESHOLD = 85.0
    POSSIBLE_MATCH_THRESHOLD = 70.0

    NAME_WEIGHT = 35.0
    POWER_WEIGHT = 40.0
    ALLIANCE_WEIGHT = 15.0
    CONFIDENCE_WEIGHT = 10.0

    def match_entries(
        self,
        baseline: PlayerRankingEntry,
        current: PlayerRankingEntry,
    ) -> PlayerIdentityMatch:
        """Compare two entries and return an explainable identity score."""
        reasons: list[str] = []

        if baseline.server != current.server:
            breakdown = IdentityScoreBreakdown(
                name_similarity=0.0,
                power_similarity=0.0,
                alliance_similarity=0.0,
                confidence_similarity=0.0,
                weighted_score=0.0,
            )
            return PlayerIdentityMatch(
                baseline=baseline,
                current=current,
                score=0.0,
                decision="no_match",
                breakdown=breakdown,
                reasons=[
                    f"Server mismatch: {baseline.server} != {current.server}.",
                ],
            )

        name_similarity = self._name_similarity(
            baseline.player_name,
            current.player_name,
        )
        power_similarity = self._power_similarity(
            baseline.hero_power,
            current.hero_power,
        )
        alliance_similarity = self._alliance_similarity(
            baseline.alliance_tag,
            current.alliance_tag,
        )
        confidence_similarity = self._confidence_similarity(
            baseline.confidence,
            current.confidence,
        )

        weighted_score = (
            name_similarity * self.NAME_WEIGHT
            + power_similarity * self.POWER_WEIGHT
            + alliance_similarity * self.ALLIANCE_WEIGHT
            + confidence_similarity * self.CONFIDENCE_WEIGHT
        )

        score = round(weighted_score, 2)

        if score >= self.MATCH_THRESHOLD:
            decision = "match"
        elif score >= self.POSSIBLE_MATCH_THRESHOLD:
            decision = "possible_match"
        else:
            decision = "no_match"

        reasons.append(f"Name similarity: {name_similarity:.2f}.")
        reasons.append(f"Hero power similarity: {power_similarity:.2f}.")
        reasons.append(f"Alliance similarity: {alliance_similarity:.2f}.")
        reasons.append(f"Confidence contribution: {confidence_similarity:.2f}.")

        return PlayerIdentityMatch(
            baseline=baseline,
            current=current,
            score=score,
            decision=decision,
            breakdown=IdentityScoreBreakdown(
                name_similarity=round(name_similarity, 4),
                power_similarity=round(power_similarity, 4),
                alliance_similarity=round(alliance_similarity, 4),
                confidence_similarity=round(confidence_similarity, 4),
                weighted_score=score,
            ),
            reasons=reasons,
        )

    def match_snapshots(
        self,
        baseline_snapshot: PlayerRankingSnapshot,
        current_snapshot: PlayerRankingSnapshot,
    ) -> PlayerSnapshotMatchResult:
        """Greedily match entries from two snapshots by highest identity score."""
        matches: list[PlayerIdentityMatch] = []
        unmatched_baseline = list(baseline_snapshot.entries)
        unmatched_current = list(current_snapshot.entries)

        candidates: list[PlayerIdentityMatch] = []
        for baseline in baseline_snapshot.entries:
            for current in current_snapshot.entries:
                result = self.match_entries(baseline, current)
                if result.decision != "no_match":
                    candidates.append(result)

        candidates.sort(key=lambda item: item.score, reverse=True)

        used_baseline: set[int] = set()
        used_current: set[int] = set()

        for candidate in candidates:
            baseline_key = id(candidate.baseline)
            current_key = id(candidate.current)

            if baseline_key in used_baseline or current_key in used_current:
                continue

            used_baseline.add(baseline_key)
            used_current.add(current_key)
            matches.append(candidate)

        unmatched_baseline = [
            entry for entry in unmatched_baseline if id(entry) not in used_baseline
        ]
        unmatched_current = [
            entry for entry in unmatched_current if id(entry) not in used_current
        ]

        return PlayerSnapshotMatchResult(
            baseline_snapshot=baseline_snapshot,
            current_snapshot=current_snapshot,
            matches=matches,
            unmatched_baseline=unmatched_baseline,
            unmatched_current=unmatched_current,
        )

    @staticmethod
    def _name_similarity(
        baseline_name: str,
        current_name: str,
    ) -> float:
        baseline = PlayerIdentityMatcher._normalize_name(baseline_name)
        current = PlayerIdentityMatcher._normalize_name(current_name)

        if not baseline or not current:
            return 0.0

        return SequenceMatcher(None, baseline, current).ratio()

    @staticmethod
    def _normalize_name(value: str) -> str:
        return "".join(ch for ch in value.casefold().strip() if ch.isalnum())

    @staticmethod
    def _power_similarity(
        baseline_power: int,
        current_power: int,
    ) -> float:
        if baseline_power <= 0 or current_power <= 0:
            return 0.0

        larger = max(baseline_power, current_power)
        delta = abs(current_power - baseline_power) / larger

        # 0% delta => 1.0, 15%+ delta => 0.0. This allows realistic THP growth
        # while still penalizing players whose power is too far apart.
        return max(0.0, 1.0 - (delta / 0.15))

    @staticmethod
    def _alliance_similarity(
        baseline_alliance: Optional[str],
        current_alliance: Optional[str],
    ) -> float:
        baseline = (baseline_alliance or "").strip().casefold()
        current = (current_alliance or "").strip().casefold()

        if baseline and current:
            return 1.0 if baseline == current else 0.0

        if not baseline and not current:
            return 0.8

        # One side missing can be a valid alliance change or OCR miss. Keep it
        # useful but weak; name and power must carry the match.
        return 0.4

    @staticmethod
    def _confidence_similarity(
        baseline_confidence: float,
        current_confidence: float,
    ) -> float:
        confidence = (float(baseline_confidence) + float(current_confidence)) / 2.0
        return max(0.0, min(1.0, confidence))
