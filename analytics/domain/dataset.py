"""
Sentinel
Dataset Domain Model
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DatasetType(Enum):
    ALLIANCE_RANKING = "Alliance Ranking"
    THP_RANKING = "THP Ranking"
    PLAYER_RANKING = "Player Ranking"
    HERO_RANKING = "Hero Ranking"
    CITY_RANKING = "City Ranking"
    UNKNOWN = "Unknown"


class DatasetSource(Enum):
    OCR = "OCR"
    DISCORD = "Discord"
    CSV = "CSV"
    MANUAL = "Manual"
    API = "API"
    UNKNOWN = "Unknown"


@dataclass(slots=True, frozen=True)
class Dataset:
    """
    One imported dataset.

    A dataset represents one logical input, for example:
    - Alliance Top 50 screenshot import
    - THP Top 10 screenshot import
    - CSV export
    """

    id: str

    campaign_id: str
    milestone_id: str

    server: int

    dataset_type: DatasetType
    source: DatasetSource

    uploaded_at: datetime
    captured_at: datetime | None = None

    quality_score: float = 100.0
    confidence: float = 100.0

    notes: str = ""
    tags: list[str] = field(default_factory=list)