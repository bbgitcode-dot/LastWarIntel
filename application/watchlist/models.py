"""
Sentinel
Watchlist Models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from analytics.talent_intelligence.recruitment_value import RecruitmentValue
from application.assessments.models import Assessment
from application.watchlist.decision_snapshot import (
    DecisionSnapshot,
)
from application.watchlist.lifecycle import (
    WatchHistory,
)


class WatchEntityType(Enum):
    SERVER = "Server"
    ALLIANCE = "Alliance"
    PLAYER = "Player"


class WatchPriority(Enum):
    IMMEDIATE = "Immediate"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    ARCHIVE = "Archive"


@dataclass(slots=True)
class WatchTarget:
    """
    Represents one tracked intelligence object.
    """

    id: str

    entity_type: WatchEntityType

    server: int

    name: str

    priority: WatchPriority

    score: float

    reason: str

    alliance: str | None = None

    tags: list[str] = field(default_factory=list)

    history: WatchHistory = field(default_factory=WatchHistory)

    decision_snapshot: DecisionSnapshot | None = None

    assessment: Assessment | None = None

    recruitment_value: RecruitmentValue | None = None

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    last_observed_at: datetime | None = None


@dataclass(slots=True, frozen=True)
class Watchlist:
    """
    Collection of watch targets.
    """

    targets: list[WatchTarget] = field(default_factory=list)