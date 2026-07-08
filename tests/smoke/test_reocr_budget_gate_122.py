import json
import pandas as pd

from ground_truth_validator import _build_ocr_evidence_report, _row_evidence_status


def test_budgeted_reocr_is_not_reported_as_missing_evidence():
    row = pd.Series({
        "alignment_context_gap": False,
        "valid_match": True,
        "alignment_guard_status": "row_alignment_observed",
        "character_verification_candidate": True,
        "character_reocr_status": "not_requested_policy_budget",
    })
    status, reason = _row_evidence_status(row, pd.DataFrame())
    assert status == "ROW_OK_POLICY_BUDGET"
    assert "budget" in reason.lower()


def test_core_verified_crop_bleed_is_warning_not_review():
    detail = pd.DataFrame([{
        "server": 551,
        "rank": 1,
        "ocr_rank": 1,
        "ground_truth_screenshot": "screen.png",
        "ocr_source_file": "",
        "ocr_sheet": "551_total_hero_power",
        "ground_truth_row_slot": 0,
        "alignment_guard_status": "row_alignment_observed",
        "alignment_safe_for_character_verification": True,
        "alignment_context_gap": False,
        "match_method": "server_power",
        "failure_class": "matched",
        "expected_name": "Joncollins21",
        "ocr_name": "Joncollinszl",
        "verified_name_display": "Joncollins21",
        "expected_name_latin_core": "Joncollins21",
        "ocr_name_latin_core": "Joncollinszl",
        "expected_alliance_display": "PbC",
        "ocr_alliance_display": "PBC",
        "verified_alliance_display": "PbC",
        "expected_power": 416693161,
        "ocr_power": 416693161,
        "power_match": True,
        "rank_match": True,
        "valid_match": True,
        "character_verification_candidate": True,
        "verified_core_identity_match": True,
        "gold_core_blocker": False,
        "character_reocr_targets": 1,
        "character_reocr_verified_expected": 1,
        "character_reocr_verified_observed": 0,
        "character_reocr_unresolved": 0,
    }])
    debug = pd.DataFrame([{
        "server": 551,
        "rank": 1,
        "target_status": "verified_expected",
        "target_field": "player_name",
        "crop_diagnostic": "crop_field_mismatch",
        "crop_anchor_status": "field_mismatch",
    }])
    payload, rows, _fragments = _build_ocr_evidence_report(detail, debug)
    assert rows.loc[0, "row_integrity_status"] == "ROW_OK_WITH_CROP_WARNING"
    assert payload["summary"]["row_integrity_ok_rows"] == 1
    assert payload["summary"]["row_integrity_review_rows"] == 0
