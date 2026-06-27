"""
Sentinel
Intelligence Feed Models
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class IntelligenceFeedItem:
    """
    One relevant item shown on the Sentinel start page.
    """

    title: str
    summary: str
    category: str
    severity: str
    impact: float
    confidence: float
    server: int | None = None
    alliance: str | None = None
    target_url: str = ""


@dataclass(slots=True, frozen=True)
class IntelligenceFeedData:
    """
    Complete Intelligence Feed view model.
    """

    title: str = "Intelligence Feed"

    subtitle: str = "Relevant strategic changes requiring attention"

    items: list[IntelligenceFeedItem] = field(default_factory=list)

    total_events: int = 0

    visible_events: int = 0

    critical_events: int = 0

    minimum_impact: float = 70.0