import json
import pandas as pd

from ground_truth_validator import (
    _build_gold_core_character_evidence_map,
    _build_position_evidence_acquisition_bridge,
)


def _row(**overrides):
    base = {
        "server": 551,
        "rank": 20,
        "expected_name": "N E",
        "ocr_name": "N E",
        "gold_core_blocker_after_elimination": True,
        "gold_core_failure_class": "vote_warning_gate_review",
        "gold_core_failure_domain": "name_evidence",
        "gold_core_fix_lane": "safe_warning_downgrade_candidate",
        "gold_core_root_cause": "name_exact_not_proven",
        "gold_core_recommendation": "acquire_position_evidence",
        "promotion_guard_primary_blocker": "name_exact",
        "character_reocr_evidence": "[]",
    }
    base.update(overrides)
    return base


def test_authoritative_metadata_is_wired_into_position_reports():
    detail = pd.DataFrame([_row()])
    cases, positions, _ = _build_gold_core_character_evidence_map(detail)
    assert cases.iloc[0]["failure_class"] == "vote_warning_gate_review"
    assert positions.iloc[0]["failure_domain"] == "name_evidence"
    assert positions.iloc[0]["fix_lane"] == "safe_warning_downgrade_candidate"


def test_verified_separator_is_confirmed_without_creating_character():
    evidence = [{
        "field": "player_name", "position": 1, "status": "verified_expected",
        "selected": " ", "screenshot": "thp_01.png", "crop_box": [1, 2, 3, 4],
        "confidence": 1.0,
    }]
    detail = pd.DataFrame([_row(character_reocr_evidence=json.dumps(evidence))])
    _, positions, _ = _build_gold_core_character_evidence_map(detail)
    sep = positions[positions["position"] == 1].iloc[0]
    assert sep["position_type"] == "SEPARATOR"
    assert sep["position_status"] == "CONFIRMED"
    assert sep["position_reason"] == "separator_confirmed_by_position_evidence"


def test_display_only_match_is_rejected_as_unsafe_binding():
    detail = pd.DataFrame([_row()])
    _, positions, _ = _build_gold_core_character_evidence_map(detail)
    _, bridge_positions, rejected, _ = _build_position_evidence_acquisition_bridge(detail, positions)
    first = bridge_positions[bridge_positions["position"] == 0].iloc[0]
    assert first["binding_status"] == "UNSAFE_BINDING_REJECTED"
    assert first["binding_method"] == "display_only_binding_rejected"
    assert first["ground_truth_used_as_evidence"] == False
    assert not rejected.empty


def test_complete_existing_chain_is_direct_position_evidence():
    evidence = [{
        "field": "player_name", "position": 0, "status": "unresolved",
        "selected": "N", "screenshot": "thp_01.png", "crop_box": [1, 2, 3, 4],
        "confidence": 0.91,
    }]
    detail = pd.DataFrame([_row(character_reocr_evidence=json.dumps(evidence))])
    _, positions, _ = _build_gold_core_character_evidence_map(detail)
    _, bridge_positions, _, _ = _build_position_evidence_acquisition_bridge(detail, positions)
    first = bridge_positions[bridge_positions["position"] == 0].iloc[0]
    assert first["binding_status"] == "DIRECT_POSITION_EVIDENCE"
    assert first["character_created_by_bridge"] == False
    assert first["operational_truth_modified"] == False


def test_conflicting_evidence_remains_conflicting():
    evidence = [{
        "field": "player_name", "position": 0, "status": "verified_observed",
        "selected": "M", "screenshot": "thp_01.png", "crop_box": [1, 2, 3, 4],
        "confidence": 0.99,
    }]
    detail = pd.DataFrame([_row(character_reocr_evidence=json.dumps(evidence), ocr_name="M E")])
    _, positions, _ = _build_gold_core_character_evidence_map(detail)
    _, bridge_positions, _, _ = _build_position_evidence_acquisition_bridge(detail, positions)
    first = bridge_positions[bridge_positions["position"] == 0].iloc[0]
    assert first["binding_status"] == "CONFLICTING_POSITION_EVIDENCE"
