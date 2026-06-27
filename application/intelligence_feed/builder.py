"""
Sentinel
Intelligence Feed Builder
"""

from __future__ import annotations

from analytics.intelligence.models import IntelligencePriority
from analytics.server_intelligence.facade import ServerIntelligenceFacade

from application.intelligence_feed.models import (
    IntelligenceFeedData,
    IntelligenceFeedItem,
)


class IntelligenceFeedBuilder:
    """
    Builds the curated Sentinel start page.

    The feed does not show every change.
    It only shows relevant changes that deserve attention.
    """

    DEFAULT_SERVERS = [638]

    def __init__(self) -> None:
        self._server_intelligence = ServerIntelligenceFacade()

    def build(
        self,
        servers: list[int] | None = None,
        minimum_impact: float = 70.0,
    ) -> IntelligenceFeedData:
        selected_servers = servers or self.DEFAULT_SERVERS

        all_items: list[IntelligenceFeedItem] = []

        for server in selected_servers:
            all_items.extend(
                self._build_server_items(
                    server=server,
                )
            )

        visible_items = [
            item
            for item in all_items
            if item.impact >= minimum_impact
        ]

        visible_items = sorted(
            visible_items,
            key=lambda item: (
                item.impact,
                item.confidence,
            ),
            reverse=True,
        )

        critical_events = sum(
            1
            for item in visible_items
            if item.severity == "critical"
        )

        return IntelligenceFeedData(
            items=visible_items,
            total_events=len(all_items),
            visible_events=len(visible_items),
            critical_events=critical_events,
            minimum_impact=minimum_impact,
        )

    def _build_server_items(
        self,
        server: int,
    ) -> list[IntelligenceFeedItem]:
        intelligence = self._server_intelligence.analyze(
            server
        )

        items: list[IntelligenceFeedItem] = []

        for risk in intelligence.assessment.risks:
            impact = self._impact_from_priority(
                risk.priority
            )

            items.append(
                IntelligenceFeedItem(
                    title=risk.title,
                    summary=risk.summary,
                    category="Risk",
                    severity=self._severity_from_priority(
                        risk.priority
                    ),
                    impact=impact,
                    confidence=risk.confidence,
                    server=server,
                    target_url=f"/servers/{server}",
                )
            )

        for opportunity in intelligence.assessment.opportunities:
            impact = self._impact_from_priority(
                opportunity.priority
            )

            items.append(
                IntelligenceFeedItem(
                    title=opportunity.title,
                    summary=opportunity.summary,
                    category="Opportunity",
                    severity=self._severity_from_priority(
                        opportunity.priority
                    ),
                    impact=impact,
                    confidence=opportunity.confidence,
                    server=server,
                    target_url=f"/servers/{server}",
                )
            )

        return items

    @staticmethod
    def _impact_from_priority(
        priority: IntelligencePriority,
    ) -> float:
        if priority == IntelligencePriority.CRITICAL:
            return 95.0

        if priority == IntelligencePriority.HIGH:
            return 82.0

        if priority == IntelligencePriority.MEDIUM:
            return 58.0

        return 25.0

    @staticmethod
    def _severity_from_priority(
        priority: IntelligencePriority,
    ) -> str:
        if priority == IntelligencePriority.CRITICAL:
            return "critical"

        if priority == IntelligencePriority.HIGH:
            return "high"

        if priority == IntelligencePriority.MEDIUM:
            return "medium"

        return "low"