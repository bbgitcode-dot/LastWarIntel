"""
Sentinel
Pipeline
"""

from __future__ import annotations

from application.pipeline.models import PipelineResult

from analytics.alliance_intelligence.facade import (
    AllianceIntelligenceFacade,
)
from analytics.comparison.difference import EntityType
from analytics.comparison.facade import ComparisonFacade
from analytics.intelligence.facade import IntelligenceFacade
from analytics.intelligence.publisher import IntelligencePublisher
from analytics.whale.facade import WhaleFacade
from analytics.matching.models import MatchCandidate


class SentinelPipeline:
    """
    Executes one complete Sentinel intelligence run.
    """

    def __init__(self) -> None:

        self._comparison = ComparisonFacade()

        self._whale = WhaleFacade()
        self._alliance = AllianceIntelligenceFacade()

        self._publisher = IntelligencePublisher()

        self._intelligence = IntelligenceFacade()

    def run(
        self,
        baseline_players: list[MatchCandidate],
        current_players: list[MatchCandidate],
        baseline_alliances: list[MatchCandidate],
        current_alliances: list[MatchCandidate],
        server: int,
        alliance: str,
    ) -> PipelineResult:

        #
        # Compare players
        #
        player_differences = (
            self._comparison.detect_candidate_differences(
                EntityType.PLAYER,
                baseline_players,
                current_players,
            )
        )

        whale = self._whale.analyze(
            player_differences,
        )

        self._publisher.publish_many(
            whale.facts,
        )

        #
        # Compare alliances
        #
        alliance_differences = (
            self._comparison.detect_candidate_differences(
                EntityType.ALLIANCE,
                baseline_alliances,
                current_alliances,
            )
        )

        alliance_result = self._alliance.analyze(
            alliance_differences,
        )

        self._publisher.publish_many(
            alliance_result.facts,
        )

        repository = self._publisher.repository

        facts = repository.all()

        intelligence = self._intelligence.analyze_facts(
            server=server,
            alliance=alliance,
            facts=facts,
        )

        return PipelineResult(
            assessment=intelligence.assessment,
            repository=repository,
            facts=facts,
            published_facts=repository.count(),
        )