"""
LastWarIntel
Recruitment Intelligence Rules
Version: 1.0

Rules that translate detected events and scores into recruitment opportunity.
"""

from __future__ import annotations

from analytics.events.models import EventType, Severity
from analytics.intelligence.models import Rule, RuleContext, RuleResult


class RecruitmentWeights:
    ALLIANCE_LEFT_TOP10 = 25
    LARGE_POWER_LOSS = 25
    HIGH_VOLATILITY = 20
    SERVER_STILL_RELEVANT = 15
    STRONG_PLAYER_BASE = 15
    LOW_QUALITY_PENALTY = -25
    STABLE_GROWING_SERVER_PENALTY = -20


def build_recruitment_rules() -> list[Rule]:
    return [
        Rule(
            name="Alliance left Top10",
            description="Alliances leaving Top10 can indicate instability or frustration.",
            points=RecruitmentWeights.ALLIANCE_LEFT_TOP10,
            priority=10,
            evaluator=rule_alliance_left_top10,
        ),
        Rule(
            name="Large power loss",
            description="Large alliance power loss can indicate recruitment opportunity.",
            points=RecruitmentWeights.LARGE_POWER_LOSS,
            priority=20,
            evaluator=rule_large_power_loss,
        ),
        Rule(
            name="High volatility",
            description="High volatility can indicate internal restructuring.",
            points=RecruitmentWeights.HIGH_VOLATILITY,
            priority=30,
            evaluator=rule_high_volatility,
        ),
        Rule(
            name="Server still relevant",
            description="The server is strong enough to be worth diplomatic attention.",
            points=RecruitmentWeights.SERVER_STILL_RELEVANT,
            priority=40,
            evaluator=rule_server_still_relevant,
        ),
        Rule(
            name="Strong player base",
            description="A strong player base makes recruitment more attractive.",
            points=RecruitmentWeights.STRONG_PLAYER_BASE,
            priority=50,
            evaluator=rule_strong_player_base,
        ),
        Rule(
            name="Low quality penalty",
            description="Very weak servers may not justify major recruiting effort.",
            points=RecruitmentWeights.LOW_QUALITY_PENALTY,
            priority=90,
            evaluator=rule_low_quality_penalty,
        ),
        Rule(
            name="Stable growing server penalty",
            description="Growing and stable servers are less likely to provide recruitment openings.",
            points=RecruitmentWeights.STABLE_GROWING_SERVER_PENALTY,
            priority=100,
            evaluator=rule_stable_growing_server_penalty,
        ),
    ]


def rule_alliance_left_top10(context: RuleContext) -> RuleResult:
    events = [
        event for event in context.events
        if event.event_type == EventType.LEFT_TOP10
    ]

    matched = len(events) > 0
    evidence = [event.summary for event in events]

    return RuleResult(
        name="Alliance left Top10",
        matched=matched,
        points=RecruitmentWeights.ALLIANCE_LEFT_TOP10 if matched else 0,
        explanation=(
            f"{len(events)} alliance(s) left the Top10."
            if matched
            else "No alliances left the Top10."
        ),
        evidence=evidence,
        priority=10,
    )


def rule_large_power_loss(context: RuleContext) -> RuleResult:
    events = []

    for event in context.events:
        if event.event_type != EventType.POWER_CHANGED:
            continue

        percent = event.facts.get("percent", 0)

        if percent <= -10:
            events.append(event)

    matched = len(events) > 0
    evidence = [event.summary for event in events]

    return RuleResult(
        name="Large power loss",
        matched=matched,
        points=RecruitmentWeights.LARGE_POWER_LOSS if matched else 0,
        explanation=(
            f"{len(events)} alliance(s) lost at least 10% power."
            if matched
            else "No large alliance power loss detected."
        ),
        evidence=evidence,
        priority=20,
    )


def rule_high_volatility(context: RuleContext) -> RuleResult:
    volatility = context.scores.get("stability_raw", 0)

    matched = volatility >= 8

    return RuleResult(
        name="High volatility",
        matched=matched,
        points=RecruitmentWeights.HIGH_VOLATILITY if matched else 0,
        explanation=(
            f"Server volatility is {volatility:.2f}%."
            if matched
            else f"Server volatility is low ({volatility:.2f}%)."
        ),
        evidence=[
            f"Volatility: {volatility:.2f}%"
        ] if matched else [],
        priority=30,
    )


def rule_server_still_relevant(context: RuleContext) -> RuleResult:
    overall = context.scores.get("overall", 0)

    matched = overall >= 55

    return RuleResult(
        name="Server still relevant",
        matched=matched,
        points=RecruitmentWeights.SERVER_STILL_RELEVANT if matched else 0,
        explanation=(
            f"Overall score is {overall:.2f}; server is relevant enough."
            if matched
            else f"Overall score is {overall:.2f}; relevance is limited."
        ),
        evidence=[
            f"Overall score: {overall:.2f}"
        ] if matched else [],
        priority=40,
    )


def rule_strong_player_base(context: RuleContext) -> RuleResult:
    player = context.scores.get("player", 0)

    matched = player >= 65

    return RuleResult(
        name="Strong player base",
        matched=matched,
        points=RecruitmentWeights.STRONG_PLAYER_BASE if matched else 0,
        explanation=(
            f"Player score is {player:.2f}; strong individual targets may exist."
            if matched
            else f"Player score is {player:.2f}; player base is not a strong signal."
        ),
        evidence=[
            f"Player score: {player:.2f}"
        ] if matched else [],
        priority=50,
    )


def rule_low_quality_penalty(context: RuleContext) -> RuleResult:
    overall = context.scores.get("overall", 0)
    player = context.scores.get("player", 0)

    matched = overall < 40 and player < 65

    return RuleResult(
        name="Low quality penalty",
        matched=matched,
        points=RecruitmentWeights.LOW_QUALITY_PENALTY if matched else 0,
        explanation=(
            "Overall and player score are both weak; active recruiting effort may not be efficient."
            if matched
            else "No low quality penalty applied."
        ),
        evidence=[
            f"Overall score: {overall:.2f}",
            f"Player score: {player:.2f}",
        ] if matched else [],
        priority=90,
    )


def rule_stable_growing_server_penalty(context: RuleContext) -> RuleResult:
    growth = context.scores.get("growth_raw", 0)
    volatility = context.scores.get("stability_raw", 0)

    matched = growth >= 10 and volatility < 8

    return RuleResult(
        name="Stable growing server penalty",
        matched=matched,
        points=RecruitmentWeights.STABLE_GROWING_SERVER_PENALTY if matched else 0,
        explanation=(
            "Server is growing and relatively stable; recruitment openings may be limited."
            if matched
            else "No stable-growth penalty applied."
        ),
        evidence=[
            f"Growth: {growth:.2f}%",
            f"Volatility: {volatility:.2f}%",
        ] if matched else [],
        priority=100,
    )