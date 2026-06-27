"""
Sentinel
Entity Domain Model
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EntityType(Enum):
    SERVER = "Server"
    ALLIANCE = "Alliance"
    PLAYER = "Player"
    HERO = "Hero"
    CITY = "City"
    UNKNOWN = "Unknown"


@dataclass(slots=True, frozen=True)
class Entity:
    """
    A normalized entity known to Sentinel.
    """

    id: str
    entity_type: EntityType

    name: str

    server: int | None = None

    external_id: str | None = None