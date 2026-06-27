"""
Sentinel
Cockpit Builder
"""

from __future__ import annotations

from application.cockpit.models import (
    Cockpit,
    NavigationItem,
    Page,
    PageType,
    Widget,
    WidgetType,
)


class CockpitBuilder:
    """
    Builds the Sentinel cockpit structure.

    This builder does not render UI.
    It only defines information architecture.
    """

    def build(
        self,
    ) -> Cockpit:

        pages = [
            self._dashboard(),
            self._morning_intelligence(),
            self._watchlist(),
            self._recruitment(),
            self._server_intelligence(),
            self._alliance_intelligence(),
            self._player_intelligence(),
            self._breaking_news(),
            self._settings(),
        ]

        navigation = [
            NavigationItem(
                title=page.title,
                page_type=page.page_type,
                order=page.order,
            )
            for page in pages
        ]

        return Cockpit(
            title="Sentinel Cockpit",
            navigation=sorted(
                navigation,
                key=lambda item: item.order,
            ),
            pages=sorted(
                pages,
                key=lambda page: page.order,
            ),
        )

    def _dashboard(
        self,
    ) -> Page:

        return Page(
            title="Dashboard",
            page_type=PageType.DASHBOARD,
            order=1,
            widgets=[
                Widget(
                    title="Status Overview",
                    widget_type=WidgetType.STATUS,
                    order=1,
                    data_key="status_overview",
                    description="Current strategic status at a glance.",
                ),
                Widget(
                    title="Today's Priorities",
                    widget_type=WidgetType.PRIORITY_TARGETS,
                    order=2,
                    data_key="priority_targets",
                    description="Highest priority actions for today.",
                ),
                Widget(
                    title="Breaking News",
                    widget_type=WidgetType.BREAKING_NEWS,
                    order=3,
                    data_key="breaking_news",
                    description="High-impact intelligence updates.",
                ),
                Widget(
                    title="Watchlist Summary",
                    widget_type=WidgetType.WATCHLIST,
                    order=4,
                    data_key="watchlist_summary",
                    description="Current watchlist status.",
                ),
            ],
        )

    def _morning_intelligence(
        self,
    ) -> Page:

        return Page(
            title="Morning Intelligence",
            page_type=PageType.MORNING_INTELLIGENCE,
            order=2,
            widgets=[
                Widget(
                    title="Morning Report",
                    widget_type=WidgetType.REPORT,
                    order=1,
                    data_key="morning_report",
                    description="Daily intelligence briefing.",
                )
            ],
        )

    def _watchlist(
        self,
    ) -> Page:

        return Page(
            title="Watchlist",
            page_type=PageType.WATCHLIST,
            order=3,
            widgets=[
                Widget(
                    title="Watchlist Board",
                    widget_type=WidgetType.WATCHLIST,
                    order=1,
                    data_key="watchlist_board",
                    description="Tracked targets by lifecycle status.",
                ),
                Widget(
                    title="Recent Watch Events",
                    widget_type=WidgetType.TIMELINE,
                    order=2,
                    data_key="watch_events",
                    description="Recent lifecycle and intelligence events.",
                ),
            ],
        )

    def _recruitment(
        self,
    ) -> Page:

        return Page(
            title="Recruitment",
            page_type=PageType.RECRUITMENT,
            order=4,
            widgets=[
                Widget(
                    title="Recruitment Targets",
                    widget_type=WidgetType.RECRUITMENT_TARGETS,
                    order=1,
                    data_key="recruitment_targets",
                    description="Ranked recruitment opportunities.",
                ),
                Widget(
                    title="Talent Profile",
                    widget_type=WidgetType.STRATEGIC_INDICATORS,
                    order=2,
                    data_key="talent_profile",
                    description="Talent and roster structure indicators.",
                ),
            ],
        )

    def _server_intelligence(
        self,
    ) -> Page:

        return Page(
            title="Server Intelligence",
            page_type=PageType.SERVER_INTELLIGENCE,
            order=5,
            widgets=[
                Widget(
                    title="Server Status",
                    widget_type=WidgetType.STATUS,
                    order=1,
                    data_key="server_status",
                    description="Strategic server assessment.",
                ),
                Widget(
                    title="Server Indicators",
                    widget_type=WidgetType.STRATEGIC_INDICATORS,
                    order=2,
                    data_key="server_indicators",
                    description="Server-level strategic indicators.",
                ),
                Widget(
                    title="Top Alliances",
                    widget_type=WidgetType.TABLE,
                    order=3,
                    data_key="top_alliances",
                    description="Most relevant alliances on the server.",
                ),
            ],
        )

    def _alliance_intelligence(
        self,
    ) -> Page:

        return Page(
            title="Alliance Intelligence",
            page_type=PageType.ALLIANCE_INTELLIGENCE,
            order=6,
            widgets=[
                Widget(
                    title="Alliance Summary",
                    widget_type=WidgetType.SUMMARY,
                    order=1,
                    data_key="alliance_summary",
                    description="Selected alliance overview.",
                ),
                Widget(
                    title="Alliance Indicators",
                    widget_type=WidgetType.STRATEGIC_INDICATORS,
                    order=2,
                    data_key="alliance_indicators",
                    description="Alliance-level strategic indicators.",
                ),
                Widget(
                    title="Decision Snapshot",
                    widget_type=WidgetType.SUMMARY,
                    order=3,
                    data_key="decision_snapshot",
                    description="Explanation for current watch decision.",
                ),
            ],
        )

    def _player_intelligence(
        self,
    ) -> Page:

        return Page(
            title="Player Intelligence",
            page_type=PageType.PLAYER_INTELLIGENCE,
            order=7,
            widgets=[
                Widget(
                    title="Player Summary",
                    widget_type=WidgetType.SUMMARY,
                    order=1,
                    data_key="player_summary",
                    description="Selected player overview.",
                ),
                Widget(
                    title="Player Timeline",
                    widget_type=WidgetType.TIMELINE,
                    order=2,
                    data_key="player_timeline",
                    description="Observed player movement history.",
                ),
            ],
        )

    def _breaking_news(
        self,
    ) -> Page:

        return Page(
            title="Breaking News",
            page_type=PageType.BREAKING_NEWS,
            order=8,
            widgets=[
                Widget(
                    title="Breaking Intelligence",
                    widget_type=WidgetType.BREAKING_NEWS,
                    order=1,
                    data_key="breaking_news",
                    description="High-impact intelligence ordered by importance.",
                )
            ],
        )

    def _settings(
        self,
    ) -> Page:

        return Page(
            title="Settings",
            page_type=PageType.SETTINGS,
            order=9,
            widgets=[
                Widget(
                    title="Configuration",
                    widget_type=WidgetType.SUMMARY,
                    order=1,
                    data_key="settings",
                    description="Sentinel configuration and thresholds.",
                )
            ],
        )