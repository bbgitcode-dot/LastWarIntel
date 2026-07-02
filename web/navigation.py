"""
Sentinel web navigation.

The visible information architecture is deliberately centered on the
Command Center workflow: Imports -> Quality -> Reviews -> Exports.  The
sidebar and workflow bar use the same navigation model so the user never has
to guess where review evidence or quality diagnostics live.
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
    description: str = ""


NAVIGATION = [
    NavigationItem("Command Center", "🎯", "/", "command", "command", "Executive overview and next action"),
    NavigationItem("Imports", "📦", "/imports", "imports", "workflow", "Runs, sources, screenshots"),
    NavigationItem("Quality", "🛡️", "/quality", "quality", "workflow", "Data Guard and validation"),
    NavigationItem("Reviews", "🔎", "/reviews", "reviews", "workflow", "Open reviews, history, evidence"),
    NavigationItem("Exports", "📈", "/reports", "reports", "workflow", "Excel and generated reports"),
    NavigationItem("Operations", "📥", "/operations", "operations", "operations", "Operational import actions"),
    NavigationItem("Servers", "🌍", "/servers", "servers", "intelligence", "Server-level intelligence"),
    NavigationItem("Alliances", "🤝", "/alliances", "alliances", "intelligence", "Alliance profiles and signals"),
    NavigationItem("Players", "👤", "/players", "players", "intelligence", "Player profiles and ranks"),
    NavigationItem("Intelligence", "🧠", "/intel", "intel", "intelligence", "Strategic assessment"),
    NavigationItem("Administration", "⚙️", "/settings", "settings", "admin", "Settings and system controls"),
]

COMMAND_WORKFLOW = [
    NavigationItem("Command", "🎯", "/", "command", "workflow", "Overview"),
    NavigationItem("Imports", "📦", "/imports", "imports", "workflow", "What was processed"),
    NavigationItem("Quality", "🛡️", "/quality", "quality", "workflow", "How trustworthy it is"),
    NavigationItem("Reviews", "🔎", "/reviews", "reviews", "workflow", "What needs a human"),
    NavigationItem("Exports", "📈", "/reports", "reports", "workflow", "What was produced"),
]
