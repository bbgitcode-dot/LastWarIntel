import pandas as pd

from ground_truth_validator import (
    _gold_blocker_strike_iii_clearance,
    _gold_core_elimination_decision,
)


def _row(**overrides):
    data = {
        "gold_core_blocker": True,
        "alignment_context_gap": False,
        "bad_match": False,
        "match_method": "server_power",
        "power_match": True,
        "core_alliance_match": True,
        "display_promotion_eligible": True,
        "expected_name": "Joker21",
        "display_reconstructed_name": "J0ker2l",
        "expected_alliance_display": "WOLF",
        "display_reconstructed_alliance_tag": "WOLF",
        "display_reconstruction_observed_votes": 0,
        "display_reconstruction_unresolved_targets": 0,
        "evidence_confirmed_fragments": 2,
        "character_reocr_verified_expected": 0,
        "character_position_action": "standard_acquisition",
        "display_confidence_decision": "eligible_high_evidence",
        "display_reconstruction_status": "name_reconstructed",
    }
    data.update(overrides)
    return pd.Series(data)


def test_strike_iii_clears_two_confusion_only_substitutions_with_full_evidence():
    ok, reason = _gold_blocker_strike_iii_clearance(_row())
    assert ok is True
    assert "two_confusion" in reason


def test_strike_iii_blocks_identity_guessing_and_unstable_positions():
    ok, reason = _gold_blocker_strike_iii_clearance(_row(expected_name="Joker21", display_reconstructed_name="Jaker2l"))
    assert ok is False
    assert reason == "strike_iii_blocked_substitution_not_confusion_family"

    ok, reason = _gold_blocker_strike_iii_clearance(_row(character_position_action="position_adaptive_multicrop_retry"))
    assert ok is False
    assert reason == "strike_iii_blocked_position_evidence_still_unstable"


def test_strike_iii_requires_evidence_for_each_changed_position():
    ok, reason = _gold_blocker_strike_iii_clearance(_row(evidence_confirmed_fragments=1))
    assert ok is False
    assert reason == "strike_iii_blocked_insufficient_confirmed_character_evidence"


def test_elimination_decision_exposes_strike_iii_without_operational_truth_change():
    decision = _gold_core_elimination_decision(_row())
    assert decision["gold_core_elimination_action"] == "clear_gold_core_blocker_strike_iii"
    assert decision["gold_core_elimination_cleared"] is True
    assert decision["gold_core_elimination_operational_truth_modified"] is False
