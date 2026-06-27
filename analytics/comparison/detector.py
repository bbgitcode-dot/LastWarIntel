"""
Sentinel
Difference Detector
"""

from __future__ import annotations

from analytics.comparison.difference import (
    Difference,
    DifferenceType,
    EntityType,
)
from analytics.comparison.models import DifferenceSet
from analytics.matching.facade import MatchingFacade
from analytics.matching.models import MatchCandidate, MatchDecision


class DifferenceDetector:
    """
    Detects generic differences between two candidate sets.

    This detector does not know whether the entities are players,
    alliances or servers. It only compares baseline and current
    candidates and emits generic differences.
    """

    def __init__(self) -> None:
        self._matching = MatchingFacade()

    def detect(
        self,
        entity_type: EntityType,
        baseline: list[MatchCandidate],
        current: list[MatchCandidate],
    ) -> DifferenceSet:
        matched_current_ids: set[str] = set()

        differences: list[Difference] = []

        for baseline_candidate in baseline:
            best_match = None

            for current_candidate in current:
                if current_candidate.identifier in matched_current_ids:
                    continue

                result = self._matching.match(
                    baseline=baseline_candidate,
                    current=current_candidate,
                )

                if result.decision == MatchDecision.NO_MATCH:
                    continue

                if best_match is None or result.confidence > best_match.confidence:
                    best_match = result

            if best_match is None:
                differences.append(
                    Difference(
                        entity_type=entity_type,
                        difference_type=DifferenceType.REMOVED,
                        identifier=baseline_candidate.identifier,
                        payload={
                            "entity_type": entity_type.value,
                            "name": baseline_candidate.name,
                            "server": baseline_candidate.server,
                            "alliance": baseline_candidate.alliance,
                            "power": baseline_candidate.power,
                        },
                    )
                )
                continue

            matched_current_ids.add(
                best_match.current.identifier
            )

            changes = self._detect_candidate_changes(
                baseline_candidate,
                best_match.current,
            )

            if changes:
                difference_type = (
                    DifferenceType.MOVED
                    if self._is_movement(changes)
                    else DifferenceType.MODIFIED
                )

                differences.append(
                    Difference(
                        entity_type=entity_type,
                        difference_type=difference_type,
                        identifier=baseline_candidate.identifier,
                        payload={
                            "entity_type": entity_type.value,
                            "matched_identifier": best_match.current.identifier,
                            "match_confidence": best_match.confidence,
                            "name": best_match.current.name,
                            "changes": changes,
                        },
                        confidence=best_match.confidence,
                    )
                )

        for current_candidate in current:
            if current_candidate.identifier in matched_current_ids:
                continue

            differences.append(
                Difference(
                    entity_type=entity_type,
                    difference_type=DifferenceType.ADDED,
                    identifier=current_candidate.identifier,
                    payload={
                        "entity_type": entity_type.value,
                        "name": current_candidate.name,
                        "server": current_candidate.server,
                        "alliance": current_candidate.alliance,
                        "power": current_candidate.power,
                    },
                )
            )

        return DifferenceSet(
            differences=differences,
        )

    @staticmethod
    def _detect_candidate_changes(
        baseline: MatchCandidate,
        current: MatchCandidate,
    ) -> dict[str, tuple[object, object]]:
        changes: dict[str, tuple[object, object]] = {}

        if baseline.server != current.server:
            changes["server"] = (
                baseline.server,
                current.server,
            )

        if baseline.alliance != current.alliance:
            changes["alliance"] = (
                baseline.alliance,
                current.alliance,
            )

        if baseline.power != current.power:
            changes["power"] = (
                baseline.power,
                current.power,
            )

        return changes

    @staticmethod
    def _is_movement(
        changes: dict[str, tuple[object, object]],
    ) -> bool:
        return (
            "server" in changes
            or "alliance" in changes
        )