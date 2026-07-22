import pandas as pd

from ground_truth_validator import (
    _apply_display_reconstruction,
    _build_gold_core_character_evidence_map,
    _build_position_evidence_acquisition_bridge,
)


def _row(**overrides):
    row = {
        "server": 551,
        "rank": 11,
        "expected_name": "Drpeek",
        "ocr_name": "Drpeek",
        "ocr_source_file": "lastwar_export.xlsx",
        "ocr_sheet": "THP",
        "screenshot": "thp_03.png",
        "row_slot": 4,
        "gold_core_blocker_after_elimination": True,
        "promotion_guard_primary_blocker": "name_exact",
        "character_reocr_evidence": "[]",
        "read_only_reocr_evidence": "[]",
    }
    row.update(overrides)
    return row


def test_display_characters_preserve_row_ocr_source_chain():
    detail = _apply_display_reconstruction(pd.DataFrame([_row()]))
    assert detail.iloc[0]["display_source_bound_characters"] == 6
    assert detail.iloc[0]["display_only_characters"] == 0
    assert "ROW_OCR_SOURCE_BOUND" in detail.iloc[0]["display_character_provenance"]


def test_bridge_uses_source_bound_offset_without_promoting_truth():
    detail = _apply_display_reconstruction(pd.DataFrame([_row()]))
    _, positions, _ = _build_gold_core_character_evidence_map(detail)
    _, bridged, _, _ = _build_position_evidence_acquisition_bridge(detail, positions)
    first = bridged[bridged["position"] == 0].iloc[0]
    assert first["binding_status"] == "BRIDGED_POSITION_EVIDENCE"
    assert first["binding_method"] == "provenance_aware_alignment"
    assert first["alignment_operation"] == "MATCH"
    assert first["display_source_screenshot"] == "thp_03.png"
    assert first["display_source_character_index"] == 0
    assert first["display_source_gold_authoritative"] == False
    assert first["operational_truth_modified"] == False


def test_authoritative_case_metadata_overrides_general_match_status():
    detail = _apply_display_reconstruction(pd.DataFrame([_row(failure_class="matched")]))
    _, positions, _ = _build_gold_core_character_evidence_map(detail)
    authoritative = pd.DataFrame([{
        "server": 551,
        "rank": 11,
        "gold_core_failure_class": "vote_warning_gate_review",
        "gold_core_failure_domain": "name_evidence",
        "gold_core_fix_lane": "safe_warning_downgrade_candidate",
        "gold_core_root_cause": "name_exact_not_proven",
        "gold_core_recommendation": "acquire_position_evidence",
    }])
    _, bridged, _, _ = _build_position_evidence_acquisition_bridge(detail, positions, authoritative)
    first = bridged.iloc[0]
    assert first["failure_class"] == "vote_warning_gate_review"
    assert first["failure_domain"] == "name_evidence"
    assert first["fix_lane"] == "safe_warning_downgrade_candidate"
