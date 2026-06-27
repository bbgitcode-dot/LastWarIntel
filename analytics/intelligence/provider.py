"""
Sentinel
Intelligence Provider
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from analytics.comparison.models import DifferenceSet
from analytics.reasoning.models import IntelligenceFact


class IntelligenceProvider(ABC):
    """
    Base class for all intelligence providers.
    """

    @property
    @abstractmethod
    def entity_name(
        self,
    ) -> str:
        """
        Human-readable provider name.
        """

    @abstractmethod
    def analyze(
        self,
        differences: DifferenceSet,
    ) -> list[IntelligenceFact]:
        """
        Analyze a DifferenceSet and produce
        IntelligenceFacts.
        """