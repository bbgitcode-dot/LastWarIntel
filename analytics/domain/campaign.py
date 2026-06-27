"""
Sentinel
Campaign Domain Model
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class CampaignType(Enum):
    SEASON = "Season"
    TRANSFER = "Transfer"
    EVENT = "Event"
    WARZONE = "Warzone"
    DESERT_STORM = "Desert Storm"
    OBSERVATION = "Observation"
    CUSTOM = "Custom"


@dataclass(slots=True, frozen=True)
class Campaign:
    """
    A campaign groups related milestones.

    Examples:
    - Season 7
    - Transfer Surge June
    - Goldvein Event
    - Desert Storm Tracking
    """

    id: str
    name: str
    campaign_type: CampaignType

    description: str = ""

    starts_at: datetime | None = None
    ends_at: datetime | None = None

    tags: list[str] = field(default_factory=list)