"""Alliance Stability capability.

This capability groups assessment rules concerned with alliance instability,
collapse risk and recruitment opportunities caused by structural weakness.
"""

from analytics.capabilities.alliance_stability.rules.alliance_collapse_rule import (
    AllianceCollapseRiskRule,
    AllianceCollapseRule,
)
from analytics.capabilities.alliance_stability.rules.recruitment_window_rule import (
    RecruitmentWindowRule,
)

__all__ = [
    "AllianceCollapseRiskRule",
    "AllianceCollapseRule",
    "RecruitmentWindowRule",
]
