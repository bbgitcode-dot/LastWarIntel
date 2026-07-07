import json

import pandas as pd

from ground_truth_validator import (
    _is_script_limited_core_identity,
    write_report,
    ValidationSummary,
)


def test_script_limited_policy_accepts_stable_mixed_latin_core():
    ok, reason = _is_script_limited_core_identity(
        accepted_match=True,
        name_category="mixed_latin_cjk",
        power_match=True,
        verified_alliance_display_exact=True,
        raw_name_normalized_match=True,
        name_normalized_similarity=1.0,
        expected_name_latin_core="MONKOPEACE",
        actual_name_latin_core="MONKOPEACE",
    )
    assert ok is True
    assert reason == "script_limited_latin_core_policy"


def test_script_limited_policy_rejects_unstable_or_latin_only_names():
    latin_only, latin_reason = _is_script_limited_core_identity(
        accepted_match=True,
        name_category="latin_only",
        power_match=True,
        verified_alliance_display_exact=True,
        raw_name_normalized_match=True,
        name_normalized_similarity=1.0,
        expected_name_latin_core="MIZZENMAST",
        actual_name_latin_core="MIZZENMAST",
    )
    assert latin_only is False
    assert latin_reason == "not_mixed_latin_cjk"

    unstable, unstable_reason = _is_script_limited_core_identity(
        accepted_match=True,
        name_category="mixed_latin_cjk",
        power_match=True,
        verified_alliance_display_exact=True,
        raw_name_normalized_match=False,
        name_normalized_similarity=0.75,
        expected_name_latin_core="IDO",
        actual_name_latin_core="OSIDO",
    )
    assert unstable is False
    assert unstable_reason == "latin_core_not_stable"


def test_write_report_exports_script_limited_policy_rows(tmp_path):
    detail = pd.DataFrame([
        {
            "rank": 3,
            "valid_match": True,
            "match_method": "server_power",
            "failure_class": "matched",
            "bad_match": False,
            "power_match": True,
            "alliance_match": True,
            "usable_identity_match": True,
            "name_exact_match": False,
            "name_normalized_match": True,
            "alliance_exact_match": True,
            "alliance_normalized_match": False,
            "power_exact_match": True,
            "rank_match": True,
            "name_display_exact_match": False,
            "alliance_display_exact_match": True,
            "exact_identity_match": False,
            "verified_name_display_exact_match": False,
            "verified_alliance_display_exact_match": True,
            "verified_exact_identity_match": False,
            "verified_identity_resolution": False,
            "verified_core_identity_match": True,
            "verified_core_identity_resolution": True,
            "script_limited_core_identity_match": True,
            "script_limited_core_identity_resolution": True,
            "script_limited_policy_reason": "script_limited_latin_core_policy",
            "identity_policy_class": "script_limited_latin_core",
            "gold_core_blocker": False,
            "identity_risk": True,
            "identity_risk_reasons": "player_name_display_drift;script_limited_core_identity;gold_fidelity_blocker",
            "high_value_identity_risk": True,
            "gold_fidelity_blocker": True,
            "character_verification_candidate": True,
            "high_value_character_verification": True,
            "character_verification_reasons": "display_character_difference",
            "character_reocr_targets": 0,
            "character_reocr_verified_expected": 0,
            "character_reocr_skipped_nonlocal": 2,
            "alignment_context_gap": False,
            "alignment_guard_status": "row_alignment_observed",
            "name_similarity": 0.8,
            "name_normalized_similarity": 1.0,
            "power_similarity": 1.0,
            "character_reocr_evidence": "[]",
            "ocr_name": "Monkopeace * 号卫",
            "ocr_alliance_display": "PbC",
            "name_category": "mixed_latin_cjk",
        }
    ])
    category = pd.DataFrame([{"name_category": "mixed_latin_cjk", "rows": 1}])
    summary = ValidationSummary(
        ground_truth_rows=1, ocr_rows=1, matched_rows=1, missing_rows=0, bad_matches=0,
        gap_blocks=0, gap_rows=0, recoverable_gap_blocks=0, recoverable_gap_rows=0,
        blocked_rank_fallbacks=0, gap_resolved_rows=0, unresolved_gap_rows=0,
        inference_rows=0, inference_accepted_rows=0, precision=1, recall=1, f1=1,
        validation_server=551, validation_ranking_type="total_hero_power", ocr_scope_rows=1,
        ocr_total_rows=1, quarantine_rows=0, quarantine_scope_rows=0,
        ground_truth_quarantined_rows=0, export_extra_rows=0, name_exact_matches=0,
        name_similarity_avg=0.8, name_normalized_similarity_avg=1, name_normalized_matches=1,
        alliance_matches=1, alliance_exact_matches=1, alliance_normalized_matches=0,
        power_matches=1, power_exact_matches=1, power_recovered_matches=0, rank_matches=1,
        usable_identity_matches=1, player_name_display_exact_matches=0,
        alliance_tag_display_exact_matches=1, exact_identity_matches=0,
        identity_risk_rows=1, high_value_identity_risk_rows=1,
        alliance_tag_case_sensitive_mismatches=0, player_name_drift_rows=1,
        identity_fidelity_score=0, character_verification_candidate_rows=1,
        high_value_character_verification_rows=1, player_name_confusable_drift_rows=0,
        alliance_tag_character_verification_rows=0, gold_fidelity_blocker_rows=1,
        player_name_display_drift_rows=1, alliance_tag_display_drift_rows=0,
        power_display_drift_rows=0, rank_display_drift_rows=0, gold_fidelity_ready=False,
        character_reocr_target_count=0, character_reocr_verified_expected=0,
        character_reocr_verified_observed=0, character_reocr_unresolved=0,
        character_reocr_skipped_nonlocal=2, score=100,
        verified_name_display_exact_matches=0, verified_alliance_display_exact_matches=1,
        verified_exact_identity_matches=0, verified_identity_resolution_rows=0,
        verified_core_identity_matches=1, verified_core_identity_resolution_rows=1,
        gold_core_blocker_rows=0, gold_core_ready=True,
        script_limited_core_identity_matches=1,
        script_limited_core_identity_resolution_rows=1,
    )

    write_report(summary, detail, category, tmp_path)
    payload = json.loads((tmp_path / "ground_truth_validation_report.json").read_text(encoding="utf-8"))
    assert payload["script_limited_policy_summary"][0]["rows"] == 1
    assert payload["script_limited_policy_rows"][0]["identity_policy_class"] == "script_limited_latin_core"
