"""
Sentinel
Cockpit Models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PageType(Enum):
    DASHBOARD = "Dashboard"
    MORNING_INTELLIGENCE = "Morning Intelligence"
    WATCHLIST = "Watchlist"
    RECRUITMENT = "Recruitment"
    SERVER_INTELLIGENCE = "Server Intelligence"
    ALLIANCE_INTELLIGENCE = "Alliance Intelligence"
    PLAYER_INTELLIGENCE = "Player Intelligence"
    BREAKING_NEWS = "Breaking News"
    SETTINGS = "Settings"


class WidgetType(Enum):
    STATUS = "Status"
    STRATEGIC_INDICATORS = "Strategic Indicators"
    PRIORITY_TARGETS = "Priority Targets"
    BREAKING_NEWS = "Breaking News"
    WATCHLIST = "Watchlist"
    RECRUITMENT_TARGETS = "Recruitment Targets"
    REPORT = "Report"
    TIMELINE = "Timeline"
    TABLE = "Table"
    SUMMARY = "Summary"


@dataclass(slots=True, frozen=True)
class NavigationItem:
    title: str
    page_type: PageType
    order: int


@dataclass(slots=True, frozen=True)
class Widget:
    title: str
    widget_type: WidgetType
    order: int
    data_key: str = ""
    description: str = ""


@dataclass(slots=True, frozen=True)
class Page:
    title: str
    page_type: PageType
    order: int
    widgets: list[Widget] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class Cockpit:
    title: str
    navigation: list[NavigationItem] = field(default_factory=list)
    pages: list[Page] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class WidgetData:
    widget_key: str
    payload: Any


@dataclass(slots=True, frozen=True)
class PageData:
    page: str
    widgets: list[WidgetData] = field(default_factory=list)