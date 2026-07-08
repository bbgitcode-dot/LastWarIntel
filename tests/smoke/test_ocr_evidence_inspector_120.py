import pandas as pd

from ground_truth_validator import _build_ocr_evidence_report


def test_ocr_evidence_marks_context_gap_as_review():
    detail = pd.DataFrame([
        {
            "server": 551,
            "rank": 21,
            "ocr_rank": 21,
            "ground_truth_screenshot": "screen.png",
            "ground_truth_row_slot": 6,
            "alignment_context_gap": True,
            "alignment_guard_status": "context_gap_no_character_verification",
            "alignment_safe_for_character_verification": False,
            "valid_match": True,
            "match_method": "inference_context_gap",
            "failure_class": "inferred_context_gap",
            "expected_name": "K9 Thunder 자주포",
            "ocr_name": "显丛显丛 X YUNS",
            "expected_alliance_display": "IVE",
            "ocr_alliance_display": "IVE",
            "verified_alliance_display": "IVE",
            "expected_power": 250009089,
            "ocr_power": 248671604,
            "power_match": False,
            "rank_match": False,
            "verified_core_identity_match": False,
            "gold_core_blocker": False,
            "character_reocr_targets": 0,
            "character_reocr_verified_expected": 0,
            "character_reocr_verified_observed": 0,
            "character_reocr_unresolved": 0,
        }
    ])
    payload, rows, fragments = _build_ocr_evidence_report(detail, pd.DataFrame())
    assert payload["summary"]["rows"] == 1
    assert payload["summary"]["row_integrity_review_rows"] == 1
    assert rows.loc[0, "row_integrity_status"] == "ROW_CONTEXT_GAP"
    assert fragments.empty


def test_ocr_evidence_preserves_reocr_fragment_provenance():
    detail = pd.DataFrame([
        {
            "server": 551,
            "rank": 1,
            "ocr_rank": 1,
            "ground_truth_screenshot": "screen.png",
            "ground_truth_row_slot": 0,
            "alignment_context_gap": False,
            "alignment_guard_status": "row_alignment_observed",
            "alignment_safe_for_character_verification": True,
            "valid_match": True,
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
            "verified_core_identity_match": True,
            "gold_core_blocker": False,
            "character_reocr_targets": 1,
            "character_reocr_verified_expected": 1,
            "character_reocr_verified_observed": 0,
            "character_reocr_unresolved": 0,
        }
    ])
    debug = pd.DataFrame([
        {
            "server": 551,
            "rank": 1,
            "screenshot": "screen.png",
            "row_slot": 0,
            "target_index": 0,
            "target_field": "player_name",
            "target_position": 10,
            "target_expected": "2",
            "target_observed": "z",
            "target_status": "verified_expected",
            "selected": "2",
            "confidence": 1.0,
            "crop_box": "[388, 124, 405, 173]",
            "crop_strategy": "player_name_after_tag",
            "crop_anchor_status": "anchor_seen",
            "crop_anchor_text": "21 | 21",
            "crop_diagnostic": "",
            "vote_texts": "21 | 21",
            "nonempty_vote_chars": "2;2",
            "debug_read": "verified_expected",
            "target_total_ms": 100.0,
            "ocr_read_ms": 90.0,
        }
    ])
    payload, rows, fragments = _build_ocr_evidence_report(detail, debug)
    assert payload["summary"]["row_integrity_ok_rows"] == 1
    assert rows.loc[0, "row_integrity_status"] == "ROW_OK_WITH_REOCR"
    assert len(fragments) == 1
    assert fragments.loc[0, "provenance"] == "character_reocr_target"
