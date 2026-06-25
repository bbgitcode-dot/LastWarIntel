"""
LastWarIntel
Application Models
Version: 1.0

Application layer models.

Reports aggregate multiple domain results but intentionally contain
no presentation logic.
"""

from __future__ import annotations

from dataclasses import dataclass

from analytics.events.facade import EventsResult
from analytics.health.facade import HealthResult
from analytics.recruitment.facade import RecruitmentResult
from analytics.timeline.facade import TimelineResult


@dataclass(slots=True)
class EntityReport:
    """
    Complete intelligence report for one alliance.
    """

    server: int
    alliance: str

    timeline: TimelineResult | None
    health: HealthResult | None
    recruitment: RecruitmentResult | None
    events: EventsResult | None


@dataclass(slots=True)
class PresidentReport:
    """
    Complete intelligence report for one server.
    """

    server: int

    timeline: dict
    health: list
    recruitment: list
    events: dict

    overall_score: float
    growth: float
    volatility: float


@dataclass(slots=True)
class RecruitmentReport:
    """
    Complete recruitment report.
    """

    server: int

    targets: list