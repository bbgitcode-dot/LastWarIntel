"""
LastWarIntel
Event Engine
Version: 1.0

Formatter for alliance event reports.

This module only formats events for human-readable output.
It does not detect events and does not calculate business logic.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from analytics.events.models import Event, EventType, Severity


class AllianceEventFormatter:
    """
    Converts alliance events into a readable CLI report.
    """

    def format(self, server: int, events: list[Event]) -> str:
        """
        Build the complete alliance event report for one server.
        """

        lines: list[str] = []

        lines.append("")
        lines.append(f"========== SERVER {server} ALLIANCE EVENTS ==========")
        lines.append("")

        if not events:
            lines.append("No alliance events detected.")
            return "\n".join(lines)

        lines.extend(self._format_summary(events))
        lines.extend(self._format_section("CRITICAL EVENTS", events, Severity.CRITICAL))
        lines.extend(self._format_section("HIGH IMPACT", events, Severity.HIGH))
        lines.extend(self._format_section("MEDIUM IMPACT", events, Severity.MEDIUM))
        lines.extend(self._format_section("LOW IMPACT", events, Severity.LOW))

        return "\n".join(lines)

    def _format_summary(self, events: list[Event]) -> list[str]:
        """
        Format a compact event summary.
        """

        lines: list[str] = []

        type_counts = Counter(event.event_type for event in events)
        severity_counts = Counter(event.severity for event in events)

        affected_entities = sorted({event.entity for event in events})

        lines.append("Summary")
        lines.append("-" * 60)
        lines.append(f"Events detected:        {len(events)}")
        lines.append(f"Affected alliances:     {len(affected_entities)}")
        lines.append(f"Critical events:        {severity_counts.get(Severity.CRITICAL, 0)}")
        lines.append(f"High impact events:     {severity_counts.get(Severity.HIGH, 0)}")
        lines.append(f"Medium impact events:   {severity_counts.get(Severity.MEDIUM, 0)}")
        lines.append(f"Low impact events:      {severity_counts.get(Severity.LOW, 0)}")
        lines.append("")

        lines.append("Event Types")
        lines.append("-" * 60)

        for event_type, count in type_counts.most_common():
            lines.append(f"{event_type.value:<25} {count}")

        lines.append("")

        return lines

    def _format_section(
        self,
        title: str,
        events: list[Event],
        severity: Severity,
    ) -> list[str]:
        """
        Format one severity section.
        """

        section_events = [
            event for event in events
            if event.severity == severity
        ]

        if not section_events:
            return []

        lines: list[str] = []

        lines.append(title)
        lines.append("-" * 60)

        grouped = self._group_by_entity(section_events)

        for entity, entity_events in grouped.items():
            lines.append(f"{entity}")

            for event in entity_events:
                lines.append(f"  {self._format_event(event)}")

                evidence = self._format_evidence(event)
                if evidence:
                    lines.append(f"    Evidence: {evidence}")

            lines.append("")

        return lines

    @staticmethod
    def _group_by_entity(events: list[Event]) -> dict[str, list[Event]]:
        """
        Group events by affected entity.
        """

        grouped: dict[str, list[Event]] = defaultdict(list)

        for event in events:
            grouped[event.entity].append(event)

        return dict(sorted(grouped.items(), key=lambda item: item[0]))

    def _format_event(self, event: Event) -> str:
        """
        Format a single event line.
        """

        if event.event_type == EventType.POWER_CHANGED:
            return self._format_power_change(event)

        if event.event_type == EventType.RANK_CHANGED:
            return self._format_rank_change(event)

        if event.event_type == EventType.ENTERED_TOP10:
            return self._format_entered_top10(event)

        if event.event_type == EventType.LEFT_TOP10:
            return self._format_left_top10(event)

        return f"{self._icon_for_event(event)} {event.summary}"

    @staticmethod
    def _format_power_change(event: Event) -> str:
        """
        Format a power change event.
        """

        percent = event.facts.get("percent")
        old_power = event.facts.get("old_power")
        new_power = event.facts.get("new_power")

        if percent is None:
            return f"● {event.summary}"

        icon = "▲" if percent >= 0 else "▼"
        direction = "gained" if percent >= 0 else "lost"

        return (
            f"{icon} Power {direction} {abs(percent):.2f}% "
            f"({format_power(old_power)} → {format_power(new_power)})"
        )

    @staticmethod
    def _format_rank_change(event: Event) -> str:
        """
        Format a rank change event.
        """

        old_rank = event.facts.get("old_rank")
        new_rank = event.facts.get("new_rank")
        rank_delta = event.facts.get("rank_delta")

        if old_rank is None or new_rank is None:
            return f"● {event.summary}"

        icon = "⇧" if rank_delta and rank_delta > 0 else "⇩"

        return f"{icon} Rank changed #{old_rank} → #{new_rank}"

    @staticmethod
    def _format_entered_top10(event: Event) -> str:
        """
        Format an entered Top10 event.
        """

        rank = event.facts.get("new_rank")
        power = event.facts.get("new_power")

        if rank is None:
            return f"★ {event.summary}"

        return f"★ Entered Top10 at rank #{rank} with {format_power(power)}"

    @staticmethod
    def _format_left_top10(event: Event) -> str:
        """
        Format a left Top10 event.
        """

        last_rank = event.facts.get("last_rank")
        last_power = event.facts.get("last_power")
        last_seen = event.facts.get("last_seen")

        if last_rank is None:
            return f"✖ {event.summary}"

        return (
            f"✖ Left Top10 after {last_seen} "
            f"(last rank #{last_rank}, {format_power(last_power)})"
        )

    @staticmethod
    def _format_evidence(event: Event) -> str:
        """
        Format evidence collections.
        """

        if not event.evidence:
            return ""

        return " → ".join(event.evidence)

    @staticmethod
    def _icon_for_event(event: Event) -> str:
        """
        Return a generic event icon.
        """

        if event.severity == Severity.CRITICAL:
            return "■"

        if event.severity == Severity.HIGH:
            return "▲"

        if event.severity == Severity.MEDIUM:
            return "●"

        return "·"


def format_power(value) -> str:
    """
    Format large power values.
    """

    if value is None:
        return "-"

    sign = "-" if value < 0 else ""
    value = abs(value)

    if value >= 1_000_000_000:
        return f"{sign}{value / 1_000_000_000:.2f}B"

    if value >= 1_000_000:
        return f"{sign}{value / 1_000_000:.2f}M"

    return f"{sign}{value:,}".replace(",", ".")