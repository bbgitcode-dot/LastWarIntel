"""Alliance Stability recruitment window rule adapter.

Recruitment Window already lives in the recruitment capability. This module
exists to keep the Alliance Stability capability package readable while avoiding
duplicate domain logic.
"""

from analytics.recruitment.assessment_rules import RecruitmentWindowRule

__all__ = ["RecruitmentWindowRule"]
