import json
import pandas as pd

from ground_truth_validator import _gold_core_elimination_decision, _gold_core_vote_policy_clearance


def _row(**overrides):
    base = {
        "gold_core_blocker": True,
        "alignment_context_gap": False,
        "match_method": "rank_exact",
        "bad_match": False,
        "power_match": True,
        "core_alliance_match": True,
        "expected_name": "GD VIP",
        "ocr_name": "GD VIP",
        "verified_name_display": "GD VIP",
        "expected_alliance_display": "WLF",
        "ocr_alliance_display": "WLF",
        "character_reocr_verified_observed": 0,
        "character_reocr_unresolved": 0,
        "character_reocr_evidence": json.dumps([{
            "field": "player_name", "position": 3, "expected": "V", "observed": "Y",
            "selected": "V", "status": "verified_expected",
            "crop_diagnostic": "vote_outside_allowed_set", "crop_anchor_status": "text_without_anchor",
        }]),
    }
    base.update(overrides)
    return pd.Series(base)


def test_vote_policy_clears_expected_only_warning_with_full_core_anchors():
    clear, reason, diagnostics = _gold_core_vote_policy_clearance(_row())
    assert clear is True
    assert reason == "vote_warning_noise_downgraded_after_expected_only_consensus"
    assert diagnostics["vote_policy_warning_items"] == 1
    decision = _gold_core_elimination_decision(_row())
    assert decision["gold_core_elimination_action"] == "clear_gold_core_blocker_vote_policy"
    assert decision["gold_core_blocker_after_elimination"] is False
    assert decision["gold_core_elimination_operational_truth_modified"] is False


def test_vote_policy_keeps_observed_counterevidence_blocked():
    row = _row(character_reocr_verified_observed=1)
    clear, reason, _ = _gold_core_vote_policy_clearance(row)
    assert clear is False
    assert reason == "vote_policy_blocked_observed_counterevidence"


def test_vote_policy_keeps_crop_geometry_conflict_blocked():
    evidence = [{
        "field": "player_name", "position": 3, "expected": "V", "observed": "Y",
        "selected": "V", "status": "verified_expected",
        "crop_diagnostic": "vote_outside_allowed_set", "crop_anchor_status": "field_mismatch",
    }]
    clear, reason, _ = _gold_core_vote_policy_clearance(_row(character_reocr_evidence=json.dumps(evidence)))
    assert clear is False
    assert reason == "vote_policy_blocked_crop_geometry_conflict"


def test_vote_policy_requires_exact_name_anchor():
    clear, reason, _ = _gold_core_vote_policy_clearance(_row(ocr_name="GD V1P", verified_name_display=""))
    assert clear is False
    assert reason == "vote_policy_blocked_name_not_exact"
