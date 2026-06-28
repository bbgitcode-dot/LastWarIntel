"""Alliance Stability assessment vocabulary.

This module contains capability-specific constants only. It deliberately avoids
execution logic so that rules remain the only place where domain conclusions
are derived.
"""

from __future__ import annotations

ALLIANCE_COLLAPSE_TITLE = "Alliance Collapse Risk"
ALLIANCE_COLLAPSE_TAGS = ("alliance_stability", "collapse", "risk")
ALLIANCE_COLLAPSE_RULE_NAME = "alliance_collapse"

STRUCTURAL_HEALTH_INDICATOR = "Structural Health"
WHALE_DENSITY_INDICATOR = "Whale Density"
ACTIVITY_INDICATOR = "Activity"

DECLINE_FACT_TAG = "decline"
WHALE_FACT_TAG = "whale"
OFFICER_FACT_TAG = "officer"
LEADERSHIP_FACT_TAG = "leadership"
POWER_LOSS_FACT_TAG = "power_loss"
MEMBER_LOSS_FACT_TAG = "member_loss"
ACTIVITY_LOSS_FACT_TAG = "activity_loss"

COLLAPSE_SUPPORT_TAGS = (
    DECLINE_FACT_TAG,
    WHALE_FACT_TAG,
    OFFICER_FACT_TAG,
    LEADERSHIP_FACT_TAG,
    POWER_LOSS_FACT_TAG,
    MEMBER_LOSS_FACT_TAG,
    ACTIVITY_LOSS_FACT_TAG,
)

__all__ = [
    "ACTIVITY_INDICATOR",
    "ACTIVITY_LOSS_FACT_TAG",
    "ALLIANCE_COLLAPSE_RULE_NAME",
    "ALLIANCE_COLLAPSE_TAGS",
    "ALLIANCE_COLLAPSE_TITLE",
    "COLLAPSE_SUPPORT_TAGS",
    "DECLINE_FACT_TAG",
    "LEADERSHIP_FACT_TAG",
    "MEMBER_LOSS_FACT_TAG",
    "OFFICER_FACT_TAG",
    "POWER_LOSS_FACT_TAG",
    "STRUCTURAL_HEALTH_INDICATOR",
    "WHALE_DENSITY_INDICATOR",
    "WHALE_FACT_TAG",
]
