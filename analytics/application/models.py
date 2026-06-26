"""
LastWarIntel
Application Models
Version: 1.4

Application layer models.

Reports aggregate multiple domain results but intentionally contain
no presentation logic.

Important:
Application models must not import facades that depend on EntityReport.
This avoids circular imports between application and domain facade layers.
"""

from __future__ import annotations

from dataclasses import dataclass

from analytics.events.facade import EventsResult
from analytics.health.facade import HealthResult
from analytics.recruitment.facade import RecruitmentResult
from analytics.timeline.facade import TimelineResult


@dataclass(slots=True, frozen=True)
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

    # Kept generic to avoid circular imports:
    # application.models -> situation.facade -> application.models
    situation: object | None = None

    # Kept generic to avoid circular imports:
    # application.models -> intelligence.facade -> application.models
    intelligence: object | None = None


@dataclass(slots=True, frozen=True)
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


@dataclass(slots=True, frozen=True)
class RecruitmentReport:
    """
    Complete recruitment report.
    """

    server: int

    targets: list