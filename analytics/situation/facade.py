"""
LastWarIntel
Situation Facade
Version: 1.0

High-level API for alliance situation analysis.
"""

from __future__ import annotations

from dataclasses import dataclass

from analytics.application.models import EntityReport
from analytics.situation.analyzer import SituationAnalyzer
from analytics.situation.models import CurrentSituation


@dataclass(slots=True, frozen=True)
class SituationResult:
    """
    Result of the situation analysis.
    """

    situation: CurrentSituation


class SituationFacade:
    """
    High-level API for situation analysis.
    """

    def __init__(self) -> None:

        self._analyzer = SituationAnalyzer()

    def analyze(
        self,
        report: EntityReport,
    ) -> SituationResult:

        return SituationResult(
            situation=self._analyzer.analyze(report),
        )