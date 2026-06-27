"""
Sentinel
Watch Status
"""

from __future__ import annotations

from enum import Enum


class WatchStatus(Enum):
    """
    Lifecycle state of one watch target.
    """

    NEW = "New"

    WATCHING = "Watching"

    ESCALATED = "Escalated"

    ACTIONED = "Actioned"

    STABLE = "Stable"

    ARCHIVED = "Archived"