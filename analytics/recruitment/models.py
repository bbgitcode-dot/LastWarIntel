"""
LastWarIntel
Recruitment Target Models
Version: 1.0
"""

from dataclasses import dataclass, field


@dataclass(slots=True)
class RecruitmentTarget:
    """
    One actionable recruitment target.
    """

    server: int
    alliance: str

    priority: int
    confidence: float

    health: int
    health_status: str
    trend: str
    risk: str

    recommendation: str

    reasons: list[str] = field(default_factory=list)