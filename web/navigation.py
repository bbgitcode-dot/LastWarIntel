"""
Sentinel
Web Navigation
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class NavigationItem:
    """
    One sidebar navigation item.
    """

    title: str
    icon: str
    url: str
    key: str


NAVIGATION = [
    NavigationItem("Command", "🏠", "/", "dashboard"),
    NavigationItem("Servers", "🗺️", "/servers", "servers"),
    NavigationItem("Alliances", "🏰", "/alliances", "alliances"),
    NavigationItem("Operations", "🚀", "/operations", "operations"),
    NavigationItem("Rankings", "📈", "/rankings", "rankings"),
    NavigationItem("Intel", "📜", "/intel", "intel"),
    NavigationItem("Settings", "⚙️", "/settings", "settings"),
]