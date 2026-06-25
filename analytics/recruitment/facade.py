"""
LastWarIntel
Recruitment Facade
Version: 1.0

High-level API for recruitment intelligence.
"""

from __future__ import annotations

from dataclasses import dataclass

from analytics.recruitment.analyzer import RecruitmentTargetAnalyzer
from analytics.recruitment.models import RecruitmentTarget


@dataclass(slots=True)
class RecruitmentResult:
    """
    Complete recruitment intelligence for one alliance.
    """

    target: RecruitmentTarget


class RecruitmentFacade:
    """
    High-level API for recruitment intelligence.
    """

    def __init__(self) -> None:
        self._analyzer = RecruitmentTargetAnalyzer()

    def analyze(
        self,
        server: int,
        alliance: str,
    ) -> RecruitmentResult | None:

        targets = self._analyzer.analyze_server(server)

        target = next(
            (
                item
                for item in targets
                if item.alliance == alliance
            ),
            None,
        )

        if target is None:
            return None

        return RecruitmentResult(target=target)

    def analyze_server(
        self,
        server: int,
    ) -> list[RecruitmentResult]:

        return [
            RecruitmentResult(target=item)
            for item in self._analyzer.analyze_server(server)
        ]