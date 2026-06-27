"""
Sentinel
Cockpit Provider
"""

from __future__ import annotations

from application.assessments.models import Assessment
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

    The provider is intentionally presentation-only.
    All business decisions are expected to be performed
    before reaching this layer.
    """

    def dashboard(
        self,
        *,
        watch_targets: list[WatchTarget],
        morning_report: Report | None,
        assessment: Assessment | None = None,
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
                        assessment=assessment,

                        #
                        # Legacy compatibility
                        #
                        overall_status=assessment.summary if assessment else self._overall_status(
                            server_health,
                            recruitment_opportunity,
                        ),
                        recommendation=assessment.recommendation if assessment else self._recommendation(
                            server_health,
                            recruitment_opportunity,
                            len(breaking_news),
                        ),
                        confidence=assessment.confidence if assessment else self._confidence(
                            server_health,
                            recruitment_opportunity,
                        ),
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

    @staticmethod
    def _overall_status(
        health: float,
        opportunity: float,
    ) -> str:

        if health < 50:
            return "Critical"

        if health < 70:
            return "Elevated Risk"

        if opportunity >= 80:
            return "Recruitment Opportunity"

        return "Stable"

    @staticmethod
    def _recommendation(
        health: float,
        opportunity: float,
        breaking_news: int,
    ) -> str:

        if opportunity >= 80:
            return "Review recruitment targets."

        if health < 60:
            return "Observe alliance stability."

        if breaking_news:
            return "Review breaking news."

        return "Continue monitoring."

    @staticmethod
    def _confidence(
        health: float,
        opportunity: float,
    ) -> float:

        return round(
            (health + opportunity) / 2,
            1,
        )