"""
LastWarIntel
Recommendation Rule

Base class for recommendation rules.
"""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from analytics.intelligence.models import (
    Recommendation,
    StrategicAssessment,
)


class RecommendationRule(ABC):
    """
    Base class for recommendation rules.
    """

    @abstractmethod
    def evaluate(
        self,
        assessment: StrategicAssessment,
    ) -> list[Recommendation]:
        """
        Produce recommendations for the given assessment.
        """
        raise NotImplementedError