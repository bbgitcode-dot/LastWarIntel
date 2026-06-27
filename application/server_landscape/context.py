"""
Sentinel
Server Landscape Context
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ServerLandscapeContext:
    """
    Context used to build the Server Landscape.
    """

    monitored_servers: list[int]

    include_incomplete: bool = True

    include_outdated: bool = True