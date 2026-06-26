"""
LastWarIntel
Entity Report Renderer
Version: 1.2

Console renderer for EntityReport.
"""

from __future__ import annotations

from analytics.application.models import EntityReport


class EntityReportRenderer:
    """
    Renders an EntityReport to the console.
    """

    @staticmethod
    def _power(value: int | float | None) -> str:
        if value is None:
            return "-"

        sign = "-" if value < 0 else ""
        value = abs(value)

        if value >= 1_000_000_000:
            return f"{sign}{value / 1_000_000_000:.2f}B"

        if value >= 1_000_000:
            return f"{sign}{value / 1_000_000:.2f}M"

        return f"{sign}{int(value):,}".replace(",", ".")

    @staticmethod
    def _section(title: str) -> None:
        print()
        print(title)
        print("-" * 70)

    def render(self, report: EntityReport) -> None:
        print()
        print("=" * 70)
        print("ALLIANCE INTELLIGENCE FILE")
        print("=" * 70)
        print()
        print(f"Server:   {report.server}")
        print(f"Alliance: {report.alliance}")

        self._render_current_situation(report)
        self._render_strategic_assessment(report)
        self._render_recommendations(report)
        self._render_timeline(report)
        self._render_timeline_metrics(report)
        self._render_timeline_trend(report)
        self._render_events(report)
        self._render_health(report)
        self._render_assessment(report)
        self._render_recruitment(report)

    def _render_current_situation(self, report: EntityReport) -> None:
        self._section("CURRENT SITUATION")

        if not report.situation:
            print("No current situation available.")
            return

        situation = report.situation.situation

        print(f"Summary:    {situation.summary}")
        print(f"Confidence: {situation.confidence:.0f}%")

        if situation.findings:
            print()
            print("Key Findings:")

            for finding in situation.findings:
                print(f"  - {finding.title}")
                print(f"    {finding.description}")
                print(f"    Confidence: {finding.confidence:.0f}%")

    def _render_strategic_assessment(self, report: EntityReport) -> None:
        self._section("STRATEGIC ASSESSMENT")

        if not report.intelligence:
            print("No strategic assessment available.")
            return

        assessment = report.intelligence.assessment

        if assessment.hypotheses:
            print("Hypotheses:")

            for hypothesis in assessment.hypotheses:
                print(f"  [{hypothesis.priority.name:<8}] {hypothesis.title}")
                print(f"    Confidence: {hypothesis.confidence:.0f}%")
                print(f"    {hypothesis.summary}")

                if hypothesis.evidence:
                    print()
                    for evidence in hypothesis.evidence:
                        print(f"      • {evidence}")

                print()
        else:
            print("Hypotheses: none")

        if assessment.risks:
            print("Strategic Risks:")

            for risk in assessment.risks:
                print(f"  [{risk.priority.name:<8}] {risk.title}")
                print(f"    Confidence: {risk.confidence:.0f}%")
                print(f"    {risk.summary}")

            print()

        if assessment.opportunities:
            print("Strategic Opportunities:")

            for opportunity in assessment.opportunities:
                print(f"  [{opportunity.priority.name:<8}] {opportunity.title}")
                print(f"    Confidence: {opportunity.confidence:.0f}%")
                print(f"    {opportunity.summary}")

            print()

        if assessment.outlook:
            print("Strategic Outlook:")
            print(f"  Confidence: {assessment.outlook.confidence:.0f}%")
            print(f"  {assessment.outlook.summary}")

    def _render_recommendations(self, report: EntityReport) -> None:
        self._section("RECOMMENDED ACTIONS")

        if (
            not report.intelligence
            or not report.intelligence.assessment.recommendations
        ):
            print("No recommendations.")
            return

        for recommendation in report.intelligence.assessment.recommendations:
            print(f"[{recommendation.priority.name:<8}] {recommendation.title}")
            print(f"  Confidence: {recommendation.confidence:.0f}%")
            print(f"  {recommendation.description}")

            if recommendation.rationale:
                print()
                for reason in recommendation.rationale:
                    print(f"    • {reason}")

            print()

    def _render_timeline(self, report: EntityReport) -> None:
        self._section("FACTS / TIMELINE")

        if not report.timeline:
            print("No timeline available.")
            return

        for point in report.timeline.timeline.points:
            print(
                f"{point.collection:<28}"
                f"Rank #{point.rank:<2} "
                f"{self._power(point.power):>10}"
            )

    def _render_timeline_metrics(self, report: EntityReport) -> None:
        self._section("TIMELINE METRICS")

        if not report.timeline:
            print("No timeline metrics available.")
            return

        metrics = report.timeline.metrics

        print(f"Snapshots:       {metrics.snapshot_count}")
        print(
            f"Power:           "
            f"{self._power(metrics.first_power)} → "
            f"{self._power(metrics.last_power)}"
        )
        print(
            f"Rank:            "
            f"#{metrics.first_rank} → "
            f"#{metrics.last_rank}"
        )
        print(f"Total Growth:    {metrics.total_growth_percent:+.2f}%")
        print(f"Max Growth:      {metrics.max_growth_percent:+.2f}%")
        print(f"Max Drop:        {metrics.max_drop_percent:+.2f}%")
        print(f"Rank Gain:       {metrics.largest_rank_gain}")
        print(f"Rank Loss:       {metrics.largest_rank_loss}")
        print(f"Volatility:      {metrics.power_volatility:.2f}%")
        print(f"Missing Latest:  {metrics.missing_latest_snapshot}")

    def _render_timeline_trend(self, report: EntityReport) -> None:
        self._section("TIMELINE TREND")

        if not report.timeline:
            print("No timeline trend available.")
            return

        trend = report.timeline.assessment

        print(f"Trend:      {trend.trend.value}")
        print(f"Confidence: {trend.confidence:.0f}%")
        print(f"Summary:    {trend.summary}")

        if trend.evidence:
            print()
            print("Evidence:")

            for evidence in trend.evidence:
                print(f"  - {evidence}")

    def _render_events(self, report: EntityReport) -> None:
        self._section("EVENTS")

        if not report.events or not report.events.events:
            print("No events detected.")
            return

        for event in report.events.events:
            print(f"[{event.severity.name:<8}] {event.event_type.value}")
            print(f"  {event.summary}")

            if event.evidence:
                print(f"  Evidence: {' → '.join(event.evidence)}")

            if event.facts:
                print("  Facts:")

                for key, value in event.facts.items():
                    if "power" in key or key == "diff":
                        value = self._power(value)
                    elif isinstance(value, float):
                        value = f"{value:.2f}"

                    print(f"    {key}: {value}")

            print()

    def _render_health(self, report: EntityReport) -> None:
        self._section("ALLIANCE HEALTH")

        if not report.health:
            print("No health assessment available.")
            return

        health = report.health.health

        print(f"Score:  {health.score}/100")
        print(f"Status: {health.status}")
        print(f"Trend:  {health.trend}")
        print(f"Risk:   {health.risk}")

        print()
        print("Reasons:")

        for reason in health.reasons:
            print(f"  - {reason}")

    def _render_assessment(self, report: EntityReport) -> None:
        self._section("ASSESSMENT / EVIDENCE")

        if not report.health:
            print("No universal assessment available.")
            return

        assessment = report.health.assessment

        print(f"Assessment: {assessment.assessment_type.value}")
        print(f"Score:      {assessment.score}/100")
        print(f"Confidence: {assessment.confidence}%")
        print(f"Summary:    {assessment.summary}")

        print()
        print("Evidence:")

        for item in assessment.evidence:
            print(f"  - [{item.source}] {item.title}")
            print(f"    {item.explanation}")
            print(
                f"    Weight: {item.weight} | "
                f"Confidence: {item.confidence}%"
            )

    def _render_recruitment(self, report: EntityReport) -> None:
        self._section("RECRUITMENT VIEW")

        if not report.recruitment:
            print("No recruitment target generated.")
            return

        target = report.recruitment.target

        print(f"Priority:       {target.priority}/100")
        print(f"Confidence:     {target.confidence}%")
        print(f"Recommendation: {target.recommendation}")
        print(f"Health:         {target.health}/100")
        print(f"Risk:           {target.risk}")

        print()
        print("Recruitment Reasons:")

        for reason in target.reasons:
            print(f"  - {reason}")