"""
Sentinel
Comparison Domain Models
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from analytics.domain.snapshot import Snapshot


@dataclass(slots=True, frozen=True)
class Comparison:
    """
    Represents a comparison between two snapshots.
    """

    baseline: Snapshot

    current: Snapshot

    @property
    def server(self) -> int:
        return self.current.server

    @property
    def campaign_id(self) -> str:
        return self.current.campaign_id

    @property
    def duration(self):
        return self.current.created_at - self.baseline.created_at

    @property
    def baseline_timestamp(self) -> datetime:
        return self.baseline.created_at

    @property
    def current_timestamp(self) -> datetime:
        return self.current.created_at