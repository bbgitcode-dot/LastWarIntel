"""
Sentinel
Report Models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ReportType(Enum):
    MORNING = "Morning"
    BREAKING_NEWS = "Breaking News"
    RECRUITMENT = "Recruitment"
    SERVER = "Server"
    ALLIANCE = "Alliance"


@dataclass(slots=True, frozen=True)
class ReportSection:
    """
    One section inside a report.
    """

    title: str

    content: list[str] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class Report:
    """
    Generic Sentinel report.
    """

    report_type: ReportType

    title: str

    generated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    sections: list[ReportSection] = field(
        default_factory=list,
    )