"""
LastWarIntel
View Formatter
Version: 1.0

Generic formatter for IntelligenceView objects.
"""

from __future__ import annotations

from analytics.views.models import IntelligenceView


class ConsoleFormatter:
    """
    Renders an IntelligenceView to the console.
    """

    LINE_WIDTH = 78

    def render(self, view: IntelligenceView) -> str:
        lines: list[str] = []

        lines.append("")
        lines.append("=" * self.LINE_WIDTH)
        lines.append(view.title)

        if view.subtitle:
            lines.append(view.subtitle)

        lines.append("=" * self.LINE_WIDTH)

        for section in view.ordered_sections:
            lines.append("")
            lines.append(section.title)
            lines.append("-" * self.LINE_WIDTH)

            if not section.items:
                lines.append("No data.")
                continue

            for item in section.items:
                lines.append(item)

        return "\n".join(lines)