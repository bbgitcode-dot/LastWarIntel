"""
LastWarIntel
Timeline Metrics
Version: 1.0

Computes reusable metrics from alliance timelines.

These metrics are intentionally domain-neutral and can be reused by
Health, Recruitment, Prediction and future Intelligence engines.
"""

from __future__ import annotations

from dataclasses import dataclass

from analytics.timeline.models import AllianceTimeline


@dataclass(slots=True)
class TimelineMetrics:
    server: int
    alliance: str

    snapshot_count: int

    first_power: int
    last_power: int

    first_rank: int
    last_rank: int

    total_growth_percent: float

    max_growth_percent: float
    max_drop_percent: float

    largest_rank_gain: int
    largest_rank_loss: int

    power_volatility: float

    missing_latest_snapshot: bool


class TimelineMetricsBuilder:
    """
    Builds objective metrics from an AllianceTimeline.
    """

    def build(
        self,
        timeline: AllianceTimeline,
    ) -> TimelineMetrics:

        points = timeline.points

        if not points:
            raise ValueError("Timeline contains no points.")

        first = points[0]
        last = points[-1]

        growth = self._growth(first.power, last.power)

        max_gain = 0.0
        max_drop = 0.0

        rank_gain = 0
        rank_loss = 0

        volatility = 0.0

        previous = points[0]

        for current in points[1:]:

            diff = self._growth(
                previous.power,
                current.power,
            )

            volatility += abs(diff)

            if diff > max_gain:
                max_gain = diff

            if diff < max_drop:
                max_drop = diff

            rank_diff = previous.rank - current.rank

            if rank_diff > rank_gain:
                rank_gain = rank_diff

            if rank_diff < rank_loss:
                rank_loss = rank_diff

            previous = current

        if len(points) > 1:
            volatility /= (len(points) - 1)

        #
        # Currently we infer this from the number of snapshots.
        # Later this will use Snapshot metadata.
        #
        missing_latest = len(points) < 3

        return TimelineMetrics(
            server=timeline.server,
            alliance=timeline.alliance,

            snapshot_count=len(points),

            first_power=first.power,
            last_power=last.power,

            first_rank=first.rank,
            last_rank=last.rank,

            total_growth_percent=growth,

            max_growth_percent=max_gain,
            max_drop_percent=max_drop,

            largest_rank_gain=rank_gain,
            largest_rank_loss=abs(rank_loss),

            power_volatility=volatility,

            missing_latest_snapshot=missing_latest,
        )

    @staticmethod
    def _growth(
        old: int,
        new: int,
    ) -> float:

        if old == 0:
            return 0.0

        return ((new - old) / old) * 100.0