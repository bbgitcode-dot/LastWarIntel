"""
Sentinel
Server Landscape Models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ServerState(Enum):
    READY = "Ready"
    PARTIAL = "Partial"
    INCOMPLETE = "Incomplete"
    OUTDATED = "Outdated"
    UNKNOWN = "Unknown"


@dataclass(slots=True, frozen=True)
class ServerCard:
    server: int
    state: ServerState

    dataset_quality: float
    activity: float

    recruitability: float
    risk: float

    last_snapshot: str
    summary: str
    assessment_available: bool


@dataclass(slots=True, frozen=True)
class ServerLandscape:
    cards: list[ServerCard] = field(default_factory=list)

    ready: int = 0
    partial: int = 0
    incomplete: int = 0
    outdated: int = 0
    unknown: int = 0