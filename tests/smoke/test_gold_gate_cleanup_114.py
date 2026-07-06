import pandas as pd

from ground_truth_validator import _build_gold_blocker_triage, write_report, ValidationSummary


def test_gold_blocker_triage_separates_rank_only_from_identity_core():
    blockers = pd.DataFrame([
        {
            "rank": 25,
            "verified_name_display_exact_match": True,
            "verified_alliance_display_exact_match": True,
            "verified_core_identity_match": True,
            "rank_match": False,
            "power_match": True,
            "power_exact_match": True,
            "alignment_context_gap": False,
            "character_reocr_skipped_nonlocal": 0,
            "character_reocr_unresolved": 0,
            "character_reocr_targets": 0,
            "high_value_identity_risk": False,
            "name_category": "latin_only",
            "identity_risk_reasons": "rank_display_only_full_fidelity_blocker;gold_fidelity_blocker",
            "character_verification_reasons": "",
            "player_name_character_verification_targets": "[]",
            "alliance_tag_character_verification_targets": "[]",
            "name_similarity": 1.0,
            "power_similarity": 1.0,
            "verified_identity_resolution": False,
            "gold_fidelity_blocker": True,
        }
    ])

    triage, summary = _build_gold_blocker_triage(blockers)

    assert triage.loc[0, "gold_blocker_class"] == "identity_core_verified_rank_only_blocker"
    assert triage.loc[0, "gold_blocker_domain"] == "rank_display"
    assert bool(triage.loc[0, "gold_blocker_is_structural"])
    assert summary.loc[0, "verified_core_identity_matches"] == 1


def test_write_report_exports_core_identity_summary(tmp_path):
    detail = pd.DataFrame([
        {
            "rank": 1,
            "valid_match": True,
            "match_method": "server_power",
            "failure_class": "matched",
            "bad_match": False,
            "power_match": True,
            "alliance_match": True,
            "usable_identity_match": True,
            "name_exact_match": True,
            "name_normalized_match": True,
            "alliance_exact_match": True,
            "alliance_normalized_match": False,
            "power_exact_match": True,
            "rank_match": False,
            "name_display_exact_match": True,
            "alliance_display_exact_match": True,
            "exact_identity_match": False,
            "verified_name_display_exact_match": True,
            "verified_alliance_display_exact_match": True,
            "verified_exact_identity_match": False,
            "verified_identity_resolution": False,
            "verified_core_identity_match": True,
            "verified_core_identity_resolution": True,
            "gold_core_blocker": False,
            "identity_risk": True,
            "identity_risk_reasons": "rank_display_only_full_fidelity_blocker;gold_fidelity_blocker",
            "high_value_identity_risk": True,
            "gold_fidelity_blocker": True,
            "character_verification_candidate": False,
            "high_value_character_verification": False,
            "character_verification_reasons": "",
            "character_reocr_targets": 0,
            "character_reocr_verified_expected": 0,
            "character_reocr_skipped_nonlocal": 0,
            "alignment_context_gap": False,
            "alignment_guard_status": "row_alignment_observed",
            "name_similarity": 1.0,
            "power_similarity": 1.0,
            "character_reocr_evidence": "[]",
            "ocr_name": "meowpenguin",
            "ocr_alliance_display": "WAP",
        }
    ])
    category = pd.DataFrame([{"name_category": "latin_only", "rows": 1}])
    summary = ValidationSummary(
        ground_truth_rows=1, ocr_rows=1, matched_rows=1, missing_rows=0, bad_matches=0,
        gap_blocks=0, gap_rows=0, recoverable_gap_blocks=0, recoverable_gap_rows=0,
        blocked_rank_fallbacks=0, gap_resolved_rows=0, unresolved_gap_rows=0,
        inference_rows=0, inference_accepted_rows=0, precision=1, recall=1, f1=1,
        validation_server=551, validation_ranking_type="total_hero_power", ocr_scope_rows=1,
        ocr_total_rows=1, quarantine_rows=0, quarantine_scope_rows=0,
        ground_truth_quarantined_rows=0, export_extra_rows=0, name_exact_matches=1,
        name_similarity_avg=1, name_normalized_similarity_avg=1, name_normalized_matches=1,
        alliance_matches=1, alliance_exact_matches=1, alliance_normalized_matches=0,
        power_matches=1, power_exact_matches=1, power_recovered_matches=0, rank_matches=0,
        usable_identity_matches=1, player_name_display_exact_matches=1,
        alliance_tag_display_exact_matches=1, exact_identity_matches=0,
        identity_risk_rows=1, high_value_identity_risk_rows=1,
        alliance_tag_case_sensitive_mismatches=0, player_name_drift_rows=0,
        identity_fidelity_score=0, character_verification_candidate_rows=0,
        high_value_character_verification_rows=0, player_name_confusable_drift_rows=0,
        alliance_tag_character_verification_rows=0, gold_fidelity_blocker_rows=1,
        player_name_display_drift_rows=0, alliance_tag_display_drift_rows=0,
        power_display_drift_rows=0, rank_display_drift_rows=1, gold_fidelity_ready=False,
        character_reocr_target_count=0, character_reocr_verified_expected=0,
        character_reocr_verified_observed=0, character_reocr_unresolved=0,
        character_reocr_skipped_nonlocal=0, score=100,
        verified_name_display_exact_matches=1, verified_alliance_display_exact_matches=1,
        verified_exact_identity_matches=0, verified_identity_resolution_rows=0,
        verified_core_identity_matches=1, verified_core_identity_resolution_rows=1,
        gold_core_blocker_rows=0, gold_core_ready=True,
    )

    write_report(summary, detail, category, tmp_path)
    report = (tmp_path / "ground_truth_validation_report.json").read_text(encoding="utf-8")
    assert "core_identity_summary" in report
    assert "gold_core_blocker_rows" in report
