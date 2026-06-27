"""
Sentinel
Snapshot Domain Model
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True, frozen=True)
class Snapshot:
    """
    A snapshot represents the combined state for one server
    at one milestone.

    A snapshot can contain multiple datasets:
    - Alliance Ranking
    - THP Ranking
    - Player Ranking
    """

    id: str

    campaign_id: str
    milestone_id: str

    server: int

    name: str = ""

    dataset_ids: list[str] = field(default_factory=list)

    created_at: datetime | None = None
    captured_at: datetime | None = None

    quality_score: float = 100.0
    confidence: float = 100.0