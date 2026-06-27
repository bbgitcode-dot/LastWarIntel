"""
Sentinel
Watch Events
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class WatchEventType(Enum):
    """
    Type of watch event.
    """

    CREATED = "Created"
    FACT = "Fact"
    INDICATOR = "Indicator"
    OPPORTUNITY = "Opportunity"
    STATUS = "Status"
    NOTE = "Note"


class WatchEventSeverity(Enum):
    """
    Severity of a watch event.
    """

    INFO = "Info"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


@dataclass(slots=True, frozen=True)
class WatchEvent:
    """
    One event attached to a watch target.
    """

    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    event_type: WatchEventType = WatchEventType.NOTE

    severity: WatchEventSeverity = WatchEventSeverity.INFO

    title: str = ""

    description: str = ""

    source: str = ""

    score_delta: float = 0.0

    tags: list[str] = field(default_factory=list)