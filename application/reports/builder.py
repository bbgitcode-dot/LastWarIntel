"""
Sentinel
Report Builder
"""

from __future__ import annotations

from application.reports.models import (
    Report,
    ReportSection,
    ReportType,
)
from application.watchlist.models import WatchTarget


class ReportBuilder:
    """
    Builds reports from Sentinel domain objects.
    """

    def morning_report(
        self,
        targets: list[WatchTarget],
    ) -> Report:

        sections: list[ReportSection] = []

        if not targets:
            sections.append(
                ReportSection(
                    title="Summary",
                    content=[
                        "No active watch targets.",
                    ],
                )
            )

            return Report(
                report_type=ReportType.MORNING,
                title="Morning Intelligence Report",
                sections=sections,
            )

        sections.append(
            ReportSection(
                title="Priority Targets",
                content=[
                    self._target_line(target)
                    for target in targets
                ],
            )
        )

        sections.append(
            ReportSection(
                title="Decision Reasons",
                content=self._decision_reasons(
                    targets,
                ),
            )
        )

        return Report(
            report_type=ReportType.MORNING,
            title="Morning Intelligence Report",
            sections=sections,
        )

    @staticmethod
    def _target_line(
        target: WatchTarget,
    ) -> str:

        snapshot = target.decision_snapshot

        if snapshot is None:
            return (
                f"{target.name} "
                f"(Score {target.score:.1f})"
            )

        return (
            f"{target.name} | "
            f"Priority={snapshot.priority} | "
            f"Health={snapshot.health:.0f} | "
            f"Talent={snapshot.talent:.0f} | "
            f"Recruitability={snapshot.recruitability:.0f} | "
            f"Opportunity={snapshot.opportunity:.0f}"
        )

    @staticmethod
    def _decision_reasons(
        targets: list[WatchTarget],
    ) -> list[str]:

        lines: list[str] = []

        for target in targets:
            snapshot = target.decision_snapshot

            if snapshot is None:
                lines.append(
                    f"{target.name}: No decision snapshot available."
                )
                continue

            if not snapshot.reasons:
                lines.append(
                    f"{target.name}: No decision reasons recorded."
                )
                continue

            for reason in snapshot.reasons:
                lines.append(
                    f"{target.name}: {reason}"
                )

        return lines