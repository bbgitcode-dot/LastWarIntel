"""
Sentinel
Cockpit Provider
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
from application.reports.models import Report
from application.watchlist.models import WatchTarget


class CockpitProvider:
    """
    Provides typed presentation models
    for cockpit pages.
    """

    def dashboard(
        self,
        *,
        watch_targets: list[WatchTarget],
        morning_report: Report | None,
        breaking_news: list[str] | None = None,
        server_health: float = 0.0,
        recruitment_opportunity: float = 0.0,
    ) -> PageData:

        breaking_news = breaking_news or []

        return PageData(
            page="Dashboard",
            widgets=[
                WidgetData(
                    widget_key="status_overview",
                    payload=DashboardStatusModel(
                        watch_target_count=len(watch_targets),
                        breaking_news_count=len(breaking_news),
                        server_health=server_health,
                        recruitment_opportunity=recruitment_opportunity,
                    ),
                ),
                WidgetData(
                    widget_key="priority_targets",
                    payload=PriorityTargetsModel(
                        targets=watch_targets[:10],
                    ),
                ),
                WidgetData(
                    widget_key="breaking_news",
                    payload=BreakingNewsModel(
                        entries=breaking_news,
                    ),
                ),
                WidgetData(
                    widget_key="morning_report",
                    payload=MorningReportModel(
                        report=morning_report,
                    )
                    if morning_report
                    else None,
                ),
            ],
        )

    def watchlist(
        self,
        watch_targets: list[WatchTarget],
    ) -> PageData:

        return PageData(
            page="Watchlist",
            widgets=[
                WidgetData(
                    widget_key="watchlist_board",
                    payload=WatchlistBoardModel(
                        targets=watch_targets,
                    ),
                ),
            ],
        )

    def recruitment(
        self,
        watch_targets: list[WatchTarget],
    ) -> PageData:

        ranked = sorted(
            watch_targets,
            key=lambda target: target.score,
            reverse=True,
        )

        return PageData(
            page="Recruitment",
            widgets=[
                WidgetData(
                    widget_key="recruitment_targets",
                    payload=RecruitmentBoardModel(
                        targets=ranked,
                    ),
                ),
            ],
        )