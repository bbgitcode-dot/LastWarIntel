"""
Sentinel
Entity Matching Facade
"""

from __future__ import annotations

from analytics.matching.matcher import EntityMatcher
from analytics.matching.models import MatchCandidate, MatchResult
from analytics.matching.player_identity import (
    PlayerIdentityMatch,
    PlayerIdentityMatcher,
    PlayerSnapshotMatchResult,
)
from models.player_ranking import PlayerRankingEntry, PlayerRankingSnapshot


class MatchingFacade:
    """
    Public entry point for entity matching.
    """

    def __init__(self) -> None:
        self._matcher = EntityMatcher()
        self._player_identity_matcher = PlayerIdentityMatcher()

    def match(
        self,
        baseline: MatchCandidate,
        current: MatchCandidate,
    ) -> MatchResult:
        return self._matcher.match(
            baseline=baseline,
            current=current,
        )

    def match_player_entries(
        self,
        baseline: PlayerRankingEntry,
        current: PlayerRankingEntry,
    ) -> PlayerIdentityMatch:
        return self._player_identity_matcher.match_entries(
            baseline=baseline,
            current=current,
        )

    def match_player_snapshots(
        self,
        baseline_snapshot: PlayerRankingSnapshot,
        current_snapshot: PlayerRankingSnapshot,
    ) -> PlayerSnapshotMatchResult:
        return self._player_identity_matcher.match_snapshots(
            baseline_snapshot=baseline_snapshot,
            current_snapshot=current_snapshot,
        )
