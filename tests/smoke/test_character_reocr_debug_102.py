import json
from pathlib import Path

import pandas as pd

from ground_truth_validator import ValidationSummary, _flatten_character_reocr_debug, write_report


def test_reocr_debug_flattens_evidence_votes():
    evidence = [{
        "field": "player_name",
        "position": 10,
        "expected": "2",
        "observed": "z",
        "screenshot": "screen.png",
        "row_slot": 0,
        "crop_box": [422, 118, 472, 173],
        "status": "unresolved",
        "selected": "",
        "confidence": 0.0,
        "crop_strategy": "player_name_after_tag",
        "text_length": 12,
        "expected_text": "Joncollins21",
        "observed_text": "Joncollinszl",
        "allowed_chars": "2Zz",
        "votes": [{"variant": "gray_x6", "text": "", "confidence": 0.0, "char": ""}],
    }]
    detail = pd.DataFrame([{
        "server": 551,
        "rank": 1,
        "ocr_rank": 1,
        "expected_name": "Joncollins21",
        "ocr_name": "Joncollinszl",
        "expected_alliance_display": "PbC",
        "ocr_alliance_display": "PBC",
        "expected_power": 416693161,
        "ocr_power": 416693161,
        "match_method": "server_power",
        "failure_class": "matched",
        "alignment_guard_status": "row_alignment_observed",
        "alignment_safe_for_character_verification": True,
        "character_verification_reasons": "same_confusion_family_difference",
        "character_reocr_evidence": json.dumps(evidence),
    }])

    debug = _flatten_character_reocr_debug(detail)

    assert len(debug) == 1
    row = debug.iloc[0]
    assert row["target_field"] == "player_name"
    assert row["crop_width"] == 50
    assert row["crop_height"] == 55
    assert row["crop_strategy"] == "player_name_after_tag"
    assert row["debug_read"] == "no_selected_char"


def test_write_report_emits_character_reocr_debug_files(tmp_path: Path):
    detail = pd.DataFrame([{
        "server": 551,
        "rank": 1,
        "match_method": "server_power",
        "bad_match": False,
        "name_exact_match": False,
        "alliance_match": True,
        "power_match": True,
        "identity_risk": True,
        "failure_class": "matched",
        "usable_identity_match": True,
        "name_display_exact_match": False,
        "alliance_display_exact_match": False,
        "exact_identity_match": False,
        "high_value_identity_risk": True,
        "character_verification_candidate": True,
        "high_value_character_verification": True,
        "gold_fidelity_blocker": True,
        "character_reocr_targets": 1,
        "character_reocr_verified_expected": 0,
        "character_reocr_verified_observed": 0,
        "character_reocr_unresolved": 1,
        "character_verification_reasons": "same_confusion_family_difference",
        "identity_risk_reasons": "targeted_character_verification_required",
        "alignment_context_gap": False,
        "alignment_guard_status": "row_alignment_observed",
        "character_reocr_evidence": '[{"field":"player_name","position":10,"expected":"2","observed":"z","screenshot":"screen.png","row_slot":0,"crop_box":[1,2,3,4],"status":"unresolved","votes":[]}]',
    }])
    category = pd.DataFrame([{"name_category": "latin_only", "rows": 1}])
    summary = ValidationSummary(
        ground_truth_rows=1, ocr_rows=1, matched_rows=1, missing_rows=0, bad_matches=0,
        gap_blocks=0, gap_rows=0, recoverable_gap_blocks=0, recoverable_gap_rows=0,
        blocked_rank_fallbacks=0, gap_resolved_rows=0, unresolved_gap_rows=0,
        inference_rows=0, inference_accepted_rows=0, precision=1.0, recall=1.0, f1=1.0,
        validation_server=551, validation_ranking_type="total_hero_power", ocr_scope_rows=1,
        ocr_total_rows=1, quarantine_rows=0, quarantine_scope_rows=0,
        ground_truth_quarantined_rows=0, export_extra_rows=0, name_exact_matches=0,
        name_similarity_avg=0.0, name_normalized_similarity_avg=0.0, name_normalized_matches=0,
        alliance_matches=1, alliance_exact_matches=1, alliance_normalized_matches=0,
        power_matches=1, power_exact_matches=1, power_recovered_matches=0, rank_matches=1,
        usable_identity_matches=1, player_name_display_exact_matches=0,
        alliance_tag_display_exact_matches=0, exact_identity_matches=0, identity_risk_rows=1,
        high_value_identity_risk_rows=1, alliance_tag_case_sensitive_mismatches=0,
        player_name_drift_rows=1, identity_fidelity_score=0.0,
        character_verification_candidate_rows=1, high_value_character_verification_rows=1,
        player_name_confusable_drift_rows=1, alliance_tag_character_verification_rows=0,
        gold_fidelity_blocker_rows=1, player_name_display_drift_rows=1,
        alliance_tag_display_drift_rows=0, power_display_drift_rows=0, rank_display_drift_rows=0,
        gold_fidelity_ready=False, character_reocr_target_count=1,
        character_reocr_verified_expected=0, character_reocr_verified_observed=0,
        character_reocr_unresolved=1, score=0.0,
    )

    write_report(summary, detail, category, tmp_path)

    assert (tmp_path / "character_reocr_debug_report.json").exists()
    assert (tmp_path / "character_reocr_debug_report.xlsx").exists()
