"""
LastWarIntel
Entity Report Renderer
Version: 1.0

Console renderer for EntityReport.
"""

from __future__ import annotations

from analytics.application.models import EntityReport


class EntityReportRenderer:
    """
    Renders an EntityReport to the console.
    """

    @staticmethod
    def _power(value: int | None) -> str:
        if value is None:
            return "-"

        sign = "-" if value < 0 else ""
        value = abs(value)

        if value >= 1_000_000_000:
            return f"{sign}{value / 1_000_000_000:.2f}B"

        if value >= 1_000_000:
            return f"{sign}{value / 1_000_000:.2f}M"

        return f"{sign}{value:,}".replace(",", ".")

    @staticmethod
    def _section(title: str):
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

        #
        # Timeline
        #

        self._section("FACTS / TIMELINE")

        if report.timeline:

            for point in report.timeline.timeline.points:

                print(
                    f"{point.collection:<28}"
                    f"Rank #{point.rank:<2} "
                    f"{self._power(point.power):>10}"
                )

        #
        # Metrics
        #

        self._section("TIMELINE METRICS")

        if report.timeline:

            m = report.timeline.metrics

            print(f"Snapshots:       {m.snapshot_count}")
            print(
                f"Power:           "
                f"{self._power(m.first_power)} → "
                f"{self._power(m.last_power)}"
            )
            print(
                f"Rank:            "
                f"#{m.first_rank} → #{m.last_rank}"
            )
            print(f"Total Growth:    {m.total_growth_percent:+.2f}%")
            print(f"Max Growth:      {m.max_growth_percent:+.2f}%")
            print(f"Max Drop:        {m.max_drop_percent:+.2f}%")
            print(f"Rank Gain:       {m.largest_rank_gain}")
            print(f"Rank Loss:       {m.largest_rank_loss}")
            print(f"Volatility:      {m.power_volatility:.2f}%")
            print(f"Missing Latest:  {m.missing_latest_snapshot}")

        #
        # Trend
        #

        self._section("TIMELINE TREND")

        if report.timeline:

            trend = report.timeline.assessment

            print(f"Trend:      {trend.trend.value}")
            print(f"Confidence: {trend.confidence:.0f}%")
            print(f"Summary:    {trend.summary}")

            if trend.evidence:

                print()
                print("Evidence:")

                for evidence in trend.evidence:
                    print(f"  - {evidence}")

        #
        # Events
        #

        self._section("EVENTS")

        if report.events and report.events.events:

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

        else:

            print("No events detected.")

        #
        # Health
        #

        self._section("ALLIANCE HEALTH")

        if report.health:

            health = report.health.health

            print(f"Score:  {health.score}/100")
            print(f"Status: {health.status}")
            print(f"Trend:  {health.trend}")
            print(f"Risk:   {health.risk}")

            print()
            print("Reasons:")

            for reason in health.reasons:
                print(f"  - {reason}")

        #
        # Assessment
        #

        self._section("ASSESSMENT / EVIDENCE")

        if report.health:

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

        #
        # Recruitment
        #

        self._section("RECRUITMENT VIEW")

        if report.recruitment:

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