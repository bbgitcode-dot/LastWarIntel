"""
LastWarIntel
Server Intelligence Analyzer
Version: 1.0

Builds strategic server-level intelligence from alliance reports.
"""

from __future__ import annotations

from analytics.application.entity_report_builder import EntityReportBuilder
from analytics.server_intelligence.models import (
    ServerHighlight,
    ServerOpportunity,
    ServerOutlook,
    ServerRisk,
    ServerSignalCategory,
    ServerSignalPriority,
    ServerStrategicAssessment,
)
from services.server_repository import ServerRepository


class ServerIntelligenceAnalyzer:
    """
    Analyzes a full server and produces strategic server intelligence.
    """

    def __init__(self) -> None:
        self._repository = ServerRepository()
        self._entity_reports = EntityReportBuilder()

    def analyze(self, server: int) -> ServerStrategicAssessment:
        histories = self._repository.get_all_alliance_histories(server)

        highlights: list[ServerHighlight] = []
        risks: list[ServerRisk] = []
        opportunities: list[ServerOpportunity] = []

        for alliance in sorted(histories.keys()):
            report = self._entity_reports.build(server, alliance)

            self._collect_timeline_signals(
                report=report,
                highlights=highlights,
                risks=risks,
                opportunities=opportunities,
            )

            self._collect_recruitment_signals(
                report=report,
                highlights=highlights,
                opportunities=opportunities,
            )

            self._collect_growth_signals(
                report=report,
                highlights=highlights,
                risks=risks,
            )

        outlook = self._build_outlook(
            risks=risks,
            opportunities=opportunities,
            highlights=highlights,
        )

        return ServerStrategicAssessment(
            server=server,
            highlights=sorted(
                highlights,
                key=lambda item: (
                    -self._priority_value(item.priority),
                    -item.confidence,
                    item.title,
                ),
            ),
            risks=sorted(
                risks,
                key=lambda item: (
                    -self._priority_value(item.priority),
                    -item.confidence,
                    item.title,
                ),
            ),
            opportunities=sorted(
                opportunities,
                key=lambda item: (
                    -self._priority_value(item.priority),
                    -item.confidence,
                    item.title,
                ),
            ),
            outlook=outlook,
        )

    def _collect_timeline_signals(
        self,
        *,
        report,
        highlights: list[ServerHighlight],
        risks: list[ServerRisk],
        opportunities: list[ServerOpportunity],
    ) -> None:
        if not report.timeline:
            return

        trend = report.timeline.assessment

        if trend.trend.value == "Collapsing":
            highlights.append(
                ServerHighlight(
                    title="Collapsing Alliance",
                    summary=(
                        f"{report.alliance} appears to be collapsing."
                    ),
                    category=ServerSignalCategory.STABILITY,
                    priority=ServerSignalPriority.CRITICAL,
                    confidence=trend.confidence,
                    entity=report.alliance,
                )
            )

            risks.append(
                ServerRisk(
                    title="Alliance Collapse",
                    summary=(
                        f"{report.alliance} disappeared from the latest snapshot."
                    ),
                    priority=ServerSignalPriority.CRITICAL,
                    confidence=trend.confidence,
                    entity=report.alliance,
                )
            )

            opportunities.append(
                ServerOpportunity(
                    title="Recruitment Window",
                    summary=(
                        f"{report.alliance} may offer immediate recruitment potential."
                    ),
                    priority=ServerSignalPriority.HIGH,
                    confidence=trend.confidence,
                    entity=report.alliance,
                )
            )

        elif trend.trend.value == "Recovering":
            highlights.append(
                ServerHighlight(
                    title="Recovering Alliance",
                    summary=(
                        f"{report.alliance} is recovering after an earlier decline."
                    ),
                    category=ServerSignalCategory.GROWTH,
                    priority=ServerSignalPriority.MEDIUM,
                    confidence=trend.confidence,
                    entity=report.alliance,
                )
            )

    def _collect_recruitment_signals(
        self,
        *,
        report,
        highlights: list[ServerHighlight],
        opportunities: list[ServerOpportunity],
    ) -> None:
        if not report.recruitment:
            return

        target = report.recruitment.target

        if target.priority >= 80:
            highlights.append(
                ServerHighlight(
                    title="High Recruitment Target",
                    summary=(
                        f"{report.alliance} is a high-priority recruitment target."
                    ),
                    category=ServerSignalCategory.RECRUITMENT,
                    priority=ServerSignalPriority.HIGH,
                    confidence=target.confidence,
                    entity=report.alliance,
                )
            )

            opportunities.append(
                ServerOpportunity(
                    title="High-Value Recruitment Target",
                    summary=(
                        f"{report.alliance} should be contacted before competitors do."
                    ),
                    priority=ServerSignalPriority.HIGH,
                    confidence=target.confidence,
                    entity=report.alliance,
                )
            )

    def _collect_growth_signals(
        self,
        *,
        report,
        highlights: list[ServerHighlight],
        risks: list[ServerRisk],
    ) -> None:
        if not report.timeline:
            return

        metrics = report.timeline.metrics

        if metrics.total_growth_percent >= 20:
            highlights.append(
                ServerHighlight(
                    title="Fast-Growing Alliance",
                    summary=(
                        f"{report.alliance} grew by "
                        f"{metrics.total_growth_percent:.2f}%."
                    ),
                    category=ServerSignalCategory.THREAT,
                    priority=ServerSignalPriority.HIGH,
                    confidence=85,
                    entity=report.alliance,
                )
            )

            risks.append(
                ServerRisk(
                    title="Emerging Competitive Threat",
                    summary=(
                        f"{report.alliance} is gaining power quickly."
                    ),
                    priority=ServerSignalPriority.HIGH,
                    confidence=85,
                    entity=report.alliance,
                )
            )

    @staticmethod
    def _build_outlook(
        *,
        risks: list[ServerRisk],
        opportunities: list[ServerOpportunity],
        highlights: list[ServerHighlight],
    ) -> ServerOutlook:
        critical_risks = [
            risk for risk in risks
            if risk.priority == ServerSignalPriority.CRITICAL
        ]

        high_opportunities = [
            opportunity for opportunity in opportunities
            if opportunity.priority in (
                ServerSignalPriority.HIGH,
                ServerSignalPriority.CRITICAL,
            )
        ]

        if critical_risks and high_opportunities:
            return ServerOutlook(
                summary=(
                    "The server shows meaningful internal restructuring "
                    "with strong recruitment opportunities."
                ),
                confidence=90,
            )

        if critical_risks:
            return ServerOutlook(
                summary=(
                    "The server shows significant instability and should be monitored closely."
                ),
                confidence=88,
            )

        if high_opportunities:
            return ServerOutlook(
                summary=(
                    "The server offers notable recruitment opportunities."
                ),
                confidence=85,
            )

        if highlights:
            return ServerOutlook(
                summary=(
                    "The server shows several strategic developments, but no critical pattern."
                ),
                confidence=75,
            )

        return ServerOutlook(
            summary="No major server-level strategic developments detected.",
            confidence=70,
        )

    @staticmethod
    def _priority_value(priority: ServerSignalPriority) -> int:
        values = {
            ServerSignalPriority.CRITICAL: 4,
            ServerSignalPriority.HIGH: 3,
            ServerSignalPriority.MEDIUM: 2,
            ServerSignalPriority.LOW: 1,
        }

        return values.get(priority, 0)