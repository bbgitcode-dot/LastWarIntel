"""
Sentinel
Milestone Domain Model
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True, frozen=True)
class Milestone:
    """
    A milestone is an ordered point inside a campaign.

    Examples:
    - Pre Transfer
    - Post Transfer
    - Week 2
    - Round 4
    - After Merge
    """

    id: str
    campaign_id: str

    name: str
    sequence: int

    description: str = ""

    starts_at: datetime | None = None
    ends_at: datetime | None = None