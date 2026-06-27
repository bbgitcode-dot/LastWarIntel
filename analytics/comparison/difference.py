"""
Sentinel
Difference Domain
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DifferenceType(Enum):
    """
    Describes how an entity changed.
    """

    ADDED = "Added"

    REMOVED = "Removed"

    MODIFIED = "Modified"

    MOVED = "Moved"


class EntityType(Enum):
    """
    Supported entity types.

    The list will grow over time as Sentinel
    gains additional intelligence capabilities.
    """

    PLAYER = "Player"

    ALLIANCE = "Alliance"

    SERVER = "Server"

    SNAPSHOT = "Snapshot"

    CAMPAIGN = "Campaign"

    STRONGHOLD = "Stronghold"

    ALTAR = "Altar"

    GOLDVEIN = "Goldvein"

    EVENT = "Event"


@dataclass(slots=True, frozen=True)
class Difference:
    """
    Generic representation of a detected difference.
    """

    entity_type: EntityType

    difference_type: DifferenceType

    identifier: str

    payload: dict[str, Any] = field(default_factory=dict)

    confidence: float = 100.0