"""
Sentinel
Entity Matching Facade
"""

from __future__ import annotations

from analytics.matching.matcher import EntityMatcher
from analytics.matching.models import MatchCandidate, MatchResult


class MatchingFacade:
    """
    Public entry point for entity matching.
    """

    def __init__(self) -> None:
        self._matcher = EntityMatcher()

    def match(
        self,
        baseline: MatchCandidate,
        current: MatchCandidate,
    ) -> MatchResult:
        return self._matcher.match(
            baseline=baseline,
            current=current,
        )