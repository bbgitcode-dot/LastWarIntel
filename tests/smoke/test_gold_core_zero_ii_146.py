import json
import pandas as pd

from ground_truth_validator import (
    _gold_core_elimination_decision,
    _gold_core_promotion_guard_clearance,
    _promotion_guard_diagnostics,
)


def _row(**overrides):
    row = {
        "server": 551,
        "rank": 50,
        "gold_core_blocker": True,
        "gold_core_failure_class": "vote_warning_gate_review",
        "alignment_context_gap": False,
        "match_method": "rank_power_alliance",
        "bad_match": False,
        "power_match": True,
        "core_alliance_match": True,
        "expected_name": "GoldWolf",
        "display_reconstructed_name": "GoldWolf",
        "verified_name_display": "GoldWolf",
        "ocr_name": "Go1dWolf",
        "expected_alliance_display": "[WLF]",
        "display_reconstructed_alliance_tag": "[WLF]",
        "verified_alliance_display": "[WLF]",
        "ocr_alliance_display": "[WLF]",
        "display_promotion_eligible": False,
        "display_promotion_block_reason": "blocked_low_coverage",
        "display_reconstruction_unresolved_targets": 0,
        "display_reconstruction_observed_votes": 0,
        "character_reocr_verified_observed": 0,
        "character_reocr_unresolved": 0,
        "character_reocr_evidence": json.dumps([{
            "field": "player_name", "position": 2, "expected": "l", "observed": "1",
            "status": "verified_expected", "selected": "l", "confidence": 0.81,
            "crop_diagnostic": "vote_outside_allowed_set", "crop_anchor_status": "text_without_anchor",
        }]),
        "display_confidence_decision": "blocked_low_evidence",
        "display_reconstruction_status": "name_reconstructed",
    }
    row.update(overrides)
    return pd.Series(row)


def test_diagnostics_expose_exact_failed_conditions():
    diagnostics = _promotion_guard_diagnostics(_row(power_match=False, display_reconstructed_name="Go1dWolf", verified_name_display=""))
    failed = json.loads(diagnostics["promotion_guard_failed_checks"])
    assert "power_proven" in failed
    assert "name_exact" in failed
    assert diagnostics["promotion_guard_primary_blocker"] in failed


def test_low_coverage_vote_warning_can_clear_with_all_mandatory_evidence():
    clear, reason, diagnostics = _gold_core_promotion_guard_clearance(_row())
    assert clear is True
    assert reason == "legacy_low_coverage_guard_rationalized_by_expected_only_consensus"
    assert diagnostics["promotion_guard_allowed_failure_class"] is True

    decision = _gold_core_elimination_decision(_row())
    assert decision["gold_core_elimination_action"] == "clear_gold_core_blocker_promotion_guard_rationalized"
    assert decision["gold_core_blocker_after_elimination"] is False
    assert decision["gold_core_elimination_operational_truth_modified"] is False


def test_crop_failure_class_never_uses_vote_override():
    clear, reason, _ = _gold_core_promotion_guard_clearance(_row(gold_core_failure_class="crop_geometry_problem"))
    assert clear is False
    assert reason == "promotion_guard_override_wrong_failure_class"


def test_observed_counterevidence_remains_blocked():
    evidence = [{
        "field": "player_name", "position": 2, "expected": "l", "observed": "1",
        "status": "verified_observed", "selected": "1",
        "crop_diagnostic": "vote_outside_allowed_set", "crop_anchor_status": "text_without_anchor",
    }]
    clear, reason, diagnostics = _gold_core_promotion_guard_clearance(
        _row(character_reocr_evidence=json.dumps(evidence), character_reocr_verified_observed=1)
    )
    assert clear is False
    assert reason.startswith("promotion_guard_override_mandatory_checks_failed")
    assert diagnostics["promotion_guard_observed_evidence"] > 0


def test_field_mismatch_remains_blocked():
    evidence = [{
        "field": "player_name", "position": 2, "expected": "l", "observed": "1",
        "status": "verified_expected", "selected": "l",
        "crop_diagnostic": "crop_field_mismatch", "crop_anchor_status": "field_mismatch",
    }]
    clear, _, diagnostics = _gold_core_promotion_guard_clearance(_row(character_reocr_evidence=json.dumps(evidence)))
    assert clear is False
    assert diagnostics["promotion_guard_field_mismatch"] is True


def test_non_low_coverage_legacy_guard_is_not_overridden():
    clear, reason, _ = _gold_core_promotion_guard_clearance(_row(display_promotion_block_reason="blocked_context_policy"))
    assert clear is False
    assert reason == "promotion_guard_override_not_low_coverage_class"
