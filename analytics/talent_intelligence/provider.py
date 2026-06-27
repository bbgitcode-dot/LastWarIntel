"""
Sentinel
Talent Indicator Provider
"""

from __future__ import annotations

from analytics.intelligence.indicators import StrategicIndicator
from analytics.matching.models import MatchCandidate
from analytics.talent_intelligence.facade import TalentIntelligenceFacade


class TalentProvider:
    """
    Provides talent value indicators.
    """

    @property
    def entity_name(
        self,
    ) -> str:
        return "Talent"

    def __init__(self) -> None:
        self._facade = TalentIntelligenceFacade()

    def analyze(
        self,
        players: list[MatchCandidate],
    ) -> list[StrategicIndicator]:

        return self._facade.analyze(players).indicators