"""
LastWarIntel
Campaign Models
Version: 1.0

Domain models for strategic campaign planning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CampaignType(Enum):
    TRANSFER = "Transfer"
    RECRUITMENT = "Recruitment"
    DIPLOMACY = "Diplomacy"


class CampaignPriority(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


@dataclass(slots=True, frozen=True)
class CampaignTarget:
    """
    One campaign target.
    """

    alliance: str

    priority: CampaignPriority

    score: float

    confidence: float

    summary: str

    rationale: list[str] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class CampaignPhase:
    """
    One campaign phase.
    """

    title: str

    targets: list[CampaignTarget] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class CampaignRisk:
    """
    Campaign risk.
    """

    title: str

    description: str

    confidence: float


@dataclass(slots=True, frozen=True)
class Campaign:
    """
    Complete campaign.
    """

    campaign_type: CampaignType

    server: int

    score: float

    confidence: float

    summary: str

    phases: list[CampaignPhase] = field(default_factory=list)

    risks: list[CampaignRisk] = field(default_factory=list)