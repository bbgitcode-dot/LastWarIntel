import pandas as pd

from ground_truth_validator import (
    _gold_blocker_strike_i_clearance,
    _gold_blocker_strike_ii_clearance,
    _gold_core_elimination_decision,
)


def _base_row(**overrides):
    data = {
        "gold_core_blocker": True,
        "alignment_context_gap": False,
        "power_match": True,
        "core_alliance_match": True,
        "display_promotion_eligible": True,
        "display_confidence_decision": "eligible_high_evidence",
        "expected_name": "Pitbullx2",
        "display_reconstructed_name": "Pibullxz",
        "expected_alliance_display": "IVE",
        "display_reconstructed_alliance_tag": "IVE",
        "display_reconstruction_observed_votes": 0,
        "display_reconstruction_unresolved_targets": 1,
        "evidence_confirmed_fragments": 2,
        "character_reocr_verified_expected": 1,
        "match_method": "server_power",
        "bad_match": False,
    }
    data.update(overrides)
    return pd.Series(data)


def test_gc001_strike_i_still_clears_single_latin_glyph():
    row = _base_row(
        expected_name="Joncollins21",
        display_reconstructed_name="Joncollins2l",
        display_reconstruction_unresolved_targets=0,
    )
    ok, reason = _gold_blocker_strike_i_clearance(row)
    assert ok is True
    assert "single_latin_glyph" in reason


def test_strike_ii_clears_missing_latin_glyph_plus_confusable_when_anchored():
    ok, reason = _gold_blocker_strike_ii_clearance(_base_row())
    assert ok is True
    assert reason == "strike_ii_one_missing_latin_glyph_plus_optional_confusable_with_full_identity_anchors"


def test_strike_ii_does_not_clear_unanchored_or_non_confusable():
    ok, reason = _gold_blocker_strike_ii_clearance(_base_row(power_match=False))
    assert ok is False
    assert reason == "strike_ii_blocked_power_not_proven"

    ok, reason = _gold_blocker_strike_ii_clearance(_base_row(expected_name="NERD", display_reconstructed_name="NER0"))
    assert ok is False
    assert reason == "strike_ii_blocked_replacement_not_confusion_family"


def test_elimination_decision_reports_strike_ii_action_without_operational_truth_change():
    decision = _gold_core_elimination_decision(_base_row())
    assert decision["gold_core_elimination_action"] == "clear_gold_core_blocker_strike_ii"
    assert decision["gold_core_elimination_cleared"] is True
    assert decision["gold_core_elimination_operational_truth_modified"] is False
