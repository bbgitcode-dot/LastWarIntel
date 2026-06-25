"""
LastWarIntel
Alliance Health Models
Version: 1.0
"""

from dataclasses import dataclass, field
from typing import Any

from analytics.events.models import Event


@dataclass(slots=True)
class AllianceHealth:
    server: int
    alliance: str
    score: int
    status: str
    trend: str
    risk: str
    reasons: list[str] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)