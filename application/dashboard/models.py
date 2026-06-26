"""
LastWarIntel
Dashboard Models
Version: 1.1

Presentation models for the web dashboard.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class DashboardMetric:
    """
    One dashboard metric.
    """

    title: str

    value: float

    maximum: float = 100.0

    unit: str = ""


@dataclass(slots=True, frozen=True)
class DashboardTarget:
    """
    One highlighted recruitment target.
    """

    alliance: str

    priority: float

    confidence: float

    summary: str


@dataclass(slots=True, frozen=True)
class DashboardCampaign:
    """
    Dashboard representation of a campaign.
    """

    summary: str

    phase_count: int

    target_count: int

    next_action: str = ""

    progress: float = 0.0

    estimated_success: float = 0.0


@dataclass(slots=True, frozen=True)
class DashboardFeedItem:
    """
    One item in the intelligence feed.
    """

    title: str

    summary: str

    severity: str

    timestamp: str


@dataclass(slots=True, frozen=True)
class DashboardData:
    """
    Complete dashboard model.
    """

    server: int

    status: str = "Operational"

    snapshot: str = "Latest available snapshot"

    metrics: list[DashboardMetric] = field(default_factory=list)

    top_targets: list[DashboardTarget] = field(default_factory=list)

    campaign: DashboardCampaign | None = None

    feed: list[DashboardFeedItem] = field(default_factory=list)

    outlook: str = ""