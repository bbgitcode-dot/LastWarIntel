"""
LastWarIntel
Event Engine
Version: 1.0

Shared domain models for all event-based intelligence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ----------------------------------------------------------------------
# Enums
# ----------------------------------------------------------------------


class EntityType(Enum):
    SERVER = "Server"
    ALLIANCE = "Alliance"
    PLAYER = "Player"


class EventType(Enum):
    POWER_CHANGED = "Power Changed"
    RANK_CHANGED = "Rank Changed"

    ENTERED_TOP10 = "Entered Top10"
    LEFT_TOP10 = "Left Top10"

    CREATED = "Created"
    DISAPPEARED = "Disappeared"


class Severity(Enum):
    LOW = 25
    MEDIUM = 50
    HIGH = 75
    CRITICAL = 100


# ----------------------------------------------------------------------
# History Models
# ----------------------------------------------------------------------


@dataclass(slots=True)
class Snapshot:
    """
    Represents one observation of an entity.
    """

    collection: str

    rank: int

    power: int


@dataclass(slots=True)
class AllianceHistory:
    """
    Complete history of one alliance across all available collections.
    """

    tag: str

    name: str

    snapshots: list[Snapshot] = field(default_factory=list)

    @property
    def first(self) -> Snapshot | None:
        return self.snapshots[0] if self.snapshots else None

    @property
    def last(self) -> Snapshot | None:
        return self.snapshots[-1] if self.snapshots else None


# ----------------------------------------------------------------------
# Event Model
# ----------------------------------------------------------------------


@dataclass(slots=True)
class Event:
    """
    Universal domain event.

    Every analyzer inside LastWarIntel produces Event objects.
    """

    event_type: EventType

    entity_type: EntityType

    entity: str

    server: int

    severity: Severity

    confidence: float

    summary: str

    facts: dict[str, Any] = field(default_factory=dict)

    evidence: list[str] = field(default_factory=list)