"""Backward-compatible THP sanity guard import.

v0.9.5.36 generalizes the THP Power Sanity Guard into the Ranking Power Sanity
Guard.  The public v0.9.5.35 function name remains available for tests and older
callers.
"""

from parser.ranking_power_sanity_guard import (  # noqa: F401
    RankingPowerSanityDecision as ThpPowerSanityDecision,
    apply_thp_power_sanity_guard,
    evaluate_ranking_power_sanity,
)
