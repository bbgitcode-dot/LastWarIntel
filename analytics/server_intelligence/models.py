"""
LastWarIntel
Server Intelligence Models
Version: 1.0

Domain models for strategic server-level intelligence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ServerSignalCategory(Enum):
    STABILITY = "Stability"
    RECRUITMENT = "Recruitment"
    GROWTH = "Growth"
    THREAT = "Threat"
    DIPLOMACY = "Diplomacy"
    TRANSFER = "Transfer"
    UNKNOWN = "Unknown"


class ServerSignalPriority(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


@dataclass(slots=True, frozen=True)
class ServerHighlight:
    """
    Important server-level highlight.
    """

    title: str
    summary: str
    category: ServerSignalCategory
    priority: ServerSignalPriority
    confidence: float
    entity: str | None = None


@dataclass(slots=True, frozen=True)
class ServerRisk:
    """
    Server-level strategic risk.
    """

    title: str
    summary: str
    priority: ServerSignalPriority
    confidence: float
    entity: str | None = None


@dataclass(slots=True, frozen=True)
class ServerOpportunity:
    """
    Server-level strategic opportunity.
    """

    title: str
    summary: str
    priority: ServerSignalPriority
    confidence: float
    entity: str | None = None


@dataclass(slots=True, frozen=True)
class ServerOutlook:
    """
    Strategic outlook for a server.
    """

    summary: str
    confidence: float


@dataclass(slots=True, frozen=True)
class ServerStrategicAssessment:
    """
    Complete strategic assessment for one server.
    """

    server: int

    highlights: list[ServerHighlight] = field(default_factory=list)
    risks: list[ServerRisk] = field(default_factory=list)
    opportunities: list[ServerOpportunity] = field(default_factory=list)

    outlook: ServerOutlook | None = None