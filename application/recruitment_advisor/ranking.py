"""
Sentinel
Recruitment Target Ranking
"""

from __future__ import annotations

from application.recruitment_advisor.models import (
    RecruitmentTarget,
)


class RecruitmentTargetRanker:
    """
    Ranks recruitment targets by strategic opportunity.
    """

    def rank(
        self,
        targets: list[RecruitmentTarget],
    ) -> list[RecruitmentTarget]:

        return sorted(
            targets,
            key=lambda target: (
                target.score,
                self._priority_value(
                    target.priority,
                ),
            ),
            reverse=True,
        )

    @staticmethod
    def _priority_value(
        priority: str,
    ) -> int:

        mapping = {
            "Critical": 4,
            "High": 3,
            "Medium": 2,
            "Low": 1,
        }

        return mapping.get(
            priority,
            0,
        )