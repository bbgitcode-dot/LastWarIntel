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
            lines.extend(
                self._render_dashboard_status(
                    payload,
                )
            )

        elif isinstance(payload, PriorityTargetsModel):
            lines.extend(
                self._render_priority_targets(
                    payload,
                )
            )

        elif isinstance(payload, WatchlistBoardModel):
            lines.extend(
                self._render_watchlist_board(
                    payload,
                )
            )

        elif isinstance(payload, RecruitmentBoardModel):
            lines.extend(
                self._render_recruitment_board(
                    payload,
                )
            )

        elif isinstance(payload, MorningReportModel):
            lines.extend(
                self._render_morning_report(
                    payload,
                )
            )

        elif isinstance(payload, BreakingNewsModel):
            lines.extend(
                self._render_breaking_news(
                    payload,
                )
            )

        else:
            lines.append(str(payload))

        lines.append("")

        return lines

    @staticmethod
    def _render_dashboard_status(
        payload: DashboardStatusModel,
    ) -> list[str]:

        return [
            f"Status              : {payload.overall_status}",
            f"Confidence          : {payload.confidence:.0f}%",
            f"Server Health       : {payload.server_health:.0f}",
            f"Recruitment Score   : {payload.recruitment_opportunity:.0f}",
            f"Watch Targets       : {payload.watch_target_count}",
            f"Breaking News       : {payload.breaking_news_count}",
            f"Recommendation      : {payload.recommendation}",
        ]

    @staticmethod
    def _render_priority_targets(
        payload: PriorityTargetsModel,
    ) -> list[str]:

        lines: list[str] = []

        if not payload.targets:
            return [
                "No priority targets.",
            ]

        for index, target in enumerate(
            payload.targets,
            start=1,
        ):
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

        return lines

    @staticmethod
    def _render_watchlist_board(
        payload: WatchlistBoardModel,
    ) -> list[str]:

        lines: list[str] = []

        if not payload.targets:
            return [
                "No watch targets.",
            ]

        for target in payload.targets:
            lines.append(
                f"{target.history.status.value:<12}"
                f"{target.name:<12}"
                f"{target.score:.0f}"
            )

        return lines

    @staticmethod
    def _render_recruitment_board(
        payload: RecruitmentBoardModel,
    ) -> list[str]:

        lines: list[str] = []

        if not payload.targets:
            return [
                "No recruitment targets.",
            ]

        for index, target in enumerate(
            payload.targets,
            start=1,
        ):
            lines.append(
                f"{index:>2}. "
                f"{target.name:<12}"
                f"{target.score:.0f}"
            )

        return lines

    @staticmethod
    def _render_morning_report(
        payload: MorningReportModel,
    ) -> list[str]:

        lines: list[str] = []

        report = payload.report

        lines.append(report.title)
        lines.append("")

        for section in report.sections:
            lines.append(section.title)

            for item in section.content:
                lines.append(f"  • {item}")

            lines.append("")

        return lines

    @staticmethod
    def _render_breaking_news(
        payload: BreakingNewsModel,
    ) -> list[str]:

        if not payload.entries:
            return [
                "No breaking news.",
            ]

        return [
            f"• {entry}"
            for entry in payload.entries
        ]