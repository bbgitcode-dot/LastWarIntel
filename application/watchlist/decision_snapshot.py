"""
Sentinel
Decision Snapshot
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from application.watchlist.status import WatchStatus


@dataclass(slots=True, frozen=True)
class DecisionSnapshot:
    """
    Immutable snapshot explaining why a watch target
    exists at a specific point in time.
    """

    created_at: datetime = field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        )
    )

    status: WatchStatus = WatchStatus.NEW

    priority: str = ""

    confidence: float = 0.0

    health: float = 0.0

    talent: float = 0.0

    recruitability: float = 0.0

    opportunity: float = 0.0

    summary: str = ""

    reasons: list[str] = field(
        default_factory=list,
    )