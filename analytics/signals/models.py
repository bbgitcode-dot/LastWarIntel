"""
LastWarIntel
Signal Models
Version: 1.0

Signals are normalized observations derived from facts, events, scores
and assessments.

They are not final interpretations.
They are reusable inputs for intelligence modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class SignalContext:
    """
    Reusable signal summary for one server.

    Intelligence modules should prefer using this context instead of
    recalculating the same event counts repeatedly.
    """

    server: int

    # Server scores / raw values
    overall: float = 0.0
    growth: float = 0.0
    volatility: float = 0.0
    player_score: float = 0.0

    # Event signals
    event_count: int = 0
    high_impact_events: int = 0
    medium_impact_events: int = 0
    low_impact_events: int = 0

    left_top10_count: int = 0
    entered_top10_count: int = 0
    power_change_count: int = 0
    rank_change_count: int = 0

    large_power_loss_count: int = 0
    large_power_gain_count: int = 0

    # Health signals
    alliance_count: int = 0
    critical_alliances: int = 0
    declining_alliances: int = 0
    unstable_alliances: int = 0
    healthy_alliances: int = 0
    excellent_alliances: int = 0

    high_risk_alliances: int = 0
    medium_risk_alliances: int = 0
    low_risk_alliances: int = 0

    # Recruitment signals
    recruitment_target_count: int = 0
    immediate_targets: int = 0
    high_priority_targets: int = 0
    watch_targets: int = 0

    # Evidence / traceability
    evidence: list[str] = field(default_factory=list)