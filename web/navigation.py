"""
Sentinel web navigation.

User-facing navigation follows the Command Center product language.  It is
intentionally broader than the currently implemented feature set so the UI can
expand without changing its information architecture every sprint.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class NavigationItem:
    """One sidebar navigation item."""

    title: str
    icon: str
    url: str
    key: str
    group: str = "main"


NAVIGATION = [
    NavigationItem("Command", "🎯", "/", "command", "mission"),
    NavigationItem("Operations", "📥", "/operations", "operations", "operations"),
    NavigationItem("Imports", "📦", "/imports", "imports", "operations"),
    NavigationItem("Data Quality", "📊", "/quality", "quality", "operations"),
    NavigationItem("Servers", "🌍", "/servers", "servers", "intelligence"),
    NavigationItem("Alliances", "🤝", "/alliances", "alliances", "intelligence"),
    NavigationItem("Players", "👤", "/players", "players", "intelligence"),
    NavigationItem("Intelligence", "🧠", "/intel", "intel", "intelligence"),
    NavigationItem("Reports", "📈", "/reports", "reports", "reports"),
    NavigationItem("Administration", "⚙️", "/settings", "settings", "admin"),
]
