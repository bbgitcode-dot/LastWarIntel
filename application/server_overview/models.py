"""
Sentinel
Server Overview Models
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class ServerOverviewMetric:
    """
    One server overview metric.
    """

    title: str
    value: float
    unit: str = ""


@dataclass(slots=True, frozen=True)
class ServerOverviewAlliance:
    """
    One alliance shown in the server overview.
    """

    alliance: str
    score: float
    summary: str
    confidence: float


@dataclass(slots=True, frozen=True)
class ServerOverviewData:
    """
    Complete server overview view model.
    """

    server: int

    status: str

    metrics: list[ServerOverviewMetric] = field(default_factory=list)

    recruitment_targets: list[ServerOverviewAlliance] = field(default_factory=list)

    growth_leaders: list[ServerOverviewAlliance] = field(default_factory=list)

    risks: list[str] = field(default_factory=list)

    opportunities: list[str] = field(default_factory=list)

    outlook: str = ""