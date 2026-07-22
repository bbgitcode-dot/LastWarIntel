import json
import pandas as pd

from ground_truth_validator import (
    _evidence_bound_name_reconstruction,
    _gold_core_evidence_name_clearance,
    _gold_core_elimination_decision,
)


def _row(**overrides):
    row = {
        "server": 551,
        "rank": 11,
        "gold_core_blocker": True,
        "gold_core_failure_class": "vote_warning_gate_review",
        "alignment_context_gap": False,
        "match_method": "rank_power_alliance",
        "bad_match": False,
        "power_match": True,
        "core_alliance_match": True,
        "expected_name": "Drpeek",
        "display_reconstructed_name": "Dxpeek",
        "verified_name_display": "Dxpeek",
        "ocr_name": "Dxpeek",
        "expected_alliance_display": "IVE",
        "display_reconstructed_alliance_tag": "IVE",
        "verified_alliance_display": "IVE",
        "ocr_alliance_display": "IVE",
        "display_promotion_eligible": False,
        "display_promotion_block_reason": "blocked_low_coverage",
        "display_reconstruction_unresolved_targets": 0,
        "display_reconstruction_observed_votes": 0,
        "character_reocr_verified_observed": 0,
        "character_reocr_unresolved": 0,
        "character_reocr_evidence": json.dumps([{
            "field": "player_name", "position": 1, "expected": "r", "observed": "x",
            "status": "verified_expected", "selected": "r", "confidence": 0.95,
            "crop_diagnostic": "vote_outside_allowed_set", "crop_anchor_status": "text_without_anchor",
            "screenshot": "shot.png", "crop_box": [1, 2, 3, 4],
        }]),
        "display_confidence_decision": "blocked_low_evidence",
        "display_reconstruction_status": "name_reconstructed",
    }
    row.update(overrides)
    return pd.Series(row)


def test_complete_position_bound_reconstruction_clears():
    diag = _evidence_bound_name_reconstruction(_row())
    assert diag["name_proof_status"] == "EVIDENCE_RECONSTRUCTED_EXACT"
    assert diag["name_reconstruction_coverage"] == 1.0
    assert diag["name_reconstruction_ground_truth_fill_used"] is False

    clear, reason, _ = _gold_core_evidence_name_clearance(_row())
    assert clear is True
    assert reason == "complete_position_bound_name_evidence_proves_expected_display"

    decision = _gold_core_elimination_decision(_row())
    assert decision["gold_core_elimination_action"] == "clear_gold_core_blocker_evidence_reconstructed_name"
    assert decision["gold_core_blocker_after_elimination"] is False
    assert decision["gold_core_elimination_operational_truth_modified"] is False


def test_partial_reconstruction_remains_blocked():
    row = _row(expected_name="Drpeek", ocr_name="Ieek", verified_name_display="Ieek", display_reconstructed_name="Ieek",
               character_reocr_evidence=json.dumps([{
                   "field": "player_name", "position": 0, "expected": "D", "observed": "I",
                   "status": "verified_expected", "selected": "D", "confidence": 1.0,
                   "crop_diagnostic": "vote_outside_allowed_set", "crop_anchor_status": "text_without_anchor",
               }]))
    diag = _evidence_bound_name_reconstruction(row)
    assert diag["name_proof_status"] == "PARTIAL_RECONSTRUCTION"
    assert diag["name_reconstruction_coverage"] < 1.0
    clear, reason, _ = _gold_core_evidence_name_clearance(row)
    assert clear is False
    assert "complete_name_evidence" in reason


def test_unknown_without_full_coverage_remains_blocked():
    row = _row(expected_name="GD VIP 지디", ocr_name="UNKNOWN", verified_name_display="UNKNOWN", display_reconstructed_name="UNKNOWN",
               character_reocr_evidence=json.dumps([{
                   "field": "player_name", "position": 0, "expected": "G", "observed": "U",
                   "status": "verified_expected", "selected": "G", "confidence": 0.8,
                   "crop_diagnostic": "vote_outside_allowed_set", "crop_anchor_status": "text_without_anchor",
               }]))
    diag = _evidence_bound_name_reconstruction(row)
    assert diag["name_proof_status"] == "PARTIAL_RECONSTRUCTION"
    assert diag["name_positions_unresolved"] > 0
    assert _gold_core_evidence_name_clearance(row)[0] is False


def test_conflicting_glyph_remains_blocked():
    evidence = [{
        "field": "player_name", "position": 1, "expected": "r", "observed": "x",
        "status": "verified_observed", "selected": "x", "confidence": 0.95,
        "crop_diagnostic": "vote_outside_allowed_set", "crop_anchor_status": "text_without_anchor",
    }]
    row = _row(character_reocr_verified_observed=1, character_reocr_evidence=json.dumps(evidence))
    diag = _evidence_bound_name_reconstruction(row)
    assert diag["name_proof_status"] == "CONFLICTING_EVIDENCE"
    assert _gold_core_evidence_name_clearance(row)[0] is False


def test_crop_mismatch_overrides_complete_reconstruction():
    evidence = [{
        "field": "player_name", "position": 1, "expected": "r", "observed": "x",
        "status": "verified_expected", "selected": "r", "confidence": 0.95,
        "crop_diagnostic": "crop_field_mismatch", "crop_anchor_status": "field_mismatch",
    }]
    row = _row(character_reocr_evidence=json.dumps(evidence))
    diag = _evidence_bound_name_reconstruction(row)
    assert diag["name_reconstruction_field_mismatch"] is True
    assert _gold_core_evidence_name_clearance(row)[0] is False


def test_alliance_or_power_mismatch_remains_blocked():
    assert _gold_core_evidence_name_clearance(_row(core_alliance_match=False, display_reconstructed_alliance_tag="BAD", verified_alliance_display="BAD", ocr_alliance_display="BAD"))[0] is False
    assert _gold_core_evidence_name_clearance(_row(power_match=False))[0] is False


def test_ground_truth_only_fill_is_never_used():
    diag = _evidence_bound_name_reconstruction(_row(expected_name="ABC", ocr_name="A", verified_name_display="A", display_reconstructed_name="A", character_reocr_evidence="[]"))
    assert diag["name_reconstructed_value"] == "A??"
    assert diag["name_reconstruction_ground_truth_fill_used"] is False
    assert diag["name_proof_status"] == "PARTIAL_RECONSTRUCTION"
