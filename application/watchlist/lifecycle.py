"""
Sentinel
Watch Lifecycle
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from application.watchlist.events import WatchEvent
from application.watchlist.status import WatchStatus


@dataclass(slots=True, frozen=True)
class WatchTransition:
    """
    Represents one lifecycle transition.
    """

    timestamp: datetime

    old_status: WatchStatus

    new_status: WatchStatus

    reason: str

    events: list[WatchEvent] = field(default_factory=list)


@dataclass(slots=True)
class WatchHistory:
    """
    Tracks lifecycle changes for one watch target.
    """

    status: WatchStatus = WatchStatus.NEW

    transitions: list[WatchTransition] = field(default_factory=list)

    def transition_to(
        self,
        new_status: WatchStatus,
        reason: str,
        events: list[WatchEvent] | None = None,
    ) -> None:

        if new_status == self.status:
            return

        self.transitions.append(
            WatchTransition(
                timestamp=datetime.now(timezone.utc),
                old_status=self.status,
                new_status=new_status,
                reason=reason,
                events=events or [],
            )
        )

        self.status = new_status

    @property
    def last_transition(
        self,
    ) -> WatchTransition | None:

        if not self.transitions:
            return None

        return self.transitions[-1]

    @property
    def age(
        self,
    ) -> int:
        """
        Number of recorded transitions.
        """

        return len(self.transitions)