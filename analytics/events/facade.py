"""
LastWarIntel
Events Facade
Version: 1.1

High-level API for alliance event intelligence.
"""

from __future__ import annotations

from dataclasses import dataclass

from analytics.events.analyzer import AllianceEventAnalyzer
from analytics.events.models import Event


@dataclass(slots=True)
class EventsResult:
    """
    Complete event intelligence for one alliance.
    """

    events: list[Event]

    @property
    def high_events(self) -> list[Event]:
        return [
            event
            for event in self.events
            if event.severity.name in ("CRITICAL", "HIGH")
        ]

    @property
    def medium_events(self) -> list[Event]:
        return [
            event
            for event in self.events
            if event.severity.name == "MEDIUM"
        ]

    @property
    def low_events(self) -> list[Event]:
        return [
            event
            for event in self.events
            if event.severity.name == "LOW"
        ]


class EventsFacade:
    """
    High-level API for event intelligence.
    """

    def __init__(self) -> None:
        self._analyzer = AllianceEventAnalyzer()

    def analyze(
        self,
        server: int,
        alliance: str,
    ) -> EventsResult:
        events = [
            event
            for event in self._analyzer.analyze(server)
            if event.entity == alliance
        ]

        return EventsResult(events=events)

    def analyze_server(
        self,
        server: int,
    ) -> dict[str, EventsResult]:
        grouped: dict[str, list[Event]] = {}

        for event in self._analyzer.analyze(server):
            grouped.setdefault(event.entity, []).append(event)

        return {
            alliance: EventsResult(events=events)
            for alliance, events in grouped.items()
        }