"""
Sentinel
Deprecated Health Fact Builder

Health Intelligence no longer produces IntelligenceFacts.

Health is now represented as StrategicIndicators.
This file remains temporarily to avoid broken imports
during the transition.
"""

from __future__ import annotations

from analytics.health_intelligence.models import HealthAssessment
from analytics.reasoning.models import IntelligenceFact


class HealthFactBuilder:
    """
    Deprecated compatibility class.

    Use HealthIndicatorBuilder instead.
    """

    def build(
        self,
        assessment: HealthAssessment,
    ) -> list[IntelligenceFact]:

        return []