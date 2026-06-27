"""
Sentinel
Cockpit Renderer
"""

from __future__ import annotations

from application.cockpit.models import (
    PageData,
    WidgetData,
)
from application.cockpit.viewmodels import (
    BreakingNewsModel,
    DashboardStatusModel,
    MorningReportModel,
    PriorityTargetsModel,
    RecruitmentBoardModel,
    WatchlistBoardModel,
)


class CockpitRenderer:
    """
    Renders cockpit pages for terminal output.
    """

    def render(
        self,
        page: PageData,
    ) -> str:

        lines: list[str] = []

        lines.append("=" * 70)
        lines.append(f"SENTINEL :: {page.page.upper()}")
        lines.append("=" * 70)
        lines.append("")

        for widget in page.widgets:
            lines.extend(
                self._render_widget(
                    widget,
                )
            )

        return "\n".join(lines)

    def _render_widget(
        self,
        widget: WidgetData,
    ) -> list[str]:

        lines: list[str] = []

        lines.append(f"[ {widget.widget_key.upper()} ]")

        payload = widget.payload

        if payload is None:
            lines.append("No data.")
            lines.append("")
            return lines

        if isinstance(payload, DashboardStatusModel):
            lines.append(
                f"Watch Targets        : {payload.watch_target_count}"
            )
            lines.append(
                f"Breaking News        : {payload.breaking_news_count}"
            )
            lines.append(
                f"Server Health        : {payload.server_health:.0f}"
            )
            lines.append(
                f"Recruitment Score    : {payload.recruitment_opportunity:.0f}"
            )

        elif isinstance(payload, PriorityTargetsModel):
            if not payload.targets:
                lines.append("No priority targets.")

            for index, target in enumerate(payload.targets, start=1):
                snapshot = target.decision_snapshot

                if snapshot:
                    lines.append(
                        f"{index:>2}. "
                        f"{target.name:<12}"
                        f" Score={target.score:.0f}"
                        f" Health={snapshot.health:.0f}"
                        f" Talent={snapshot.talent:.0f}"
                        f" Recruit={snapshot.recruitability:.0f}"
                    )
                else:
                    lines.append(
                        f"{index:>2}. {target.name}"
                    )

        elif isinstance(payload, WatchlistBoardModel):
            if not payload.targets:
                lines.append("No watch targets.")

            for target in payload.targets:
                lines.append(
                    f"{target.history.status.value:<12}"
                    f"{target.name:<12}"
                    f"{target.score:.0f}"
                )

        elif isinstance(payload, RecruitmentBoardModel):
            if not payload.targets:
                lines.append("No recruitment targets.")

            for index, target in enumerate(payload.targets, start=1):
                lines.append(
                    f"{index:>2}. "
                    f"{target.name:<12}"
                    f"{target.score:.0f}"
                )

        elif isinstance(payload, MorningReportModel):
            report = payload.report

            lines.append(report.title)
            lines.append("")

            for section in report.sections:
                lines.append(section.title)

                for item in section.content:
                    lines.append(f"  • {item}")

                lines.append("")

        elif isinstance(payload, BreakingNewsModel):
            if not payload.entries:
                lines.append("No breaking news.")
            else:
                for entry in payload.entries:
                    lines.append(f"• {entry}")

        else:
            lines.append(str(payload))

        lines.append("")

        return lines