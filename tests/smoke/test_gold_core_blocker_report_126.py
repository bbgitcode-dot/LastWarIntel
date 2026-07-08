import pandas as pd

from ground_truth_validator import _build_gold_core_blocker_report


def test_gold_core_blocker_report_keeps_only_core_blockers_and_classifies_vote_warning():
    triage = pd.DataFrame([
        {
            "server": 551,
            "rank": 8,
            "gold_core_blocker": True,
            "gold_blocker_priority": "P1",
            "gold_blocker_class": "nonlocal_or_multilingual_player_display_drift",
            "gold_blocker_domain": "player_name",
            "gold_blocker_automation_path": "multilingual_name_ocr_or_conservative_block",
            "character_reocr_verified_expected": 5,
            "character_reocr_verified_observed": 0,
            "character_reocr_unresolved": 0,
            "character_reocr_skipped_nonlocal": 7,
            "name_category": "hangul_only",
        },
        {
            "server": 551,
            "rank": 1,
            "gold_core_blocker": False,
            "gold_blocker_priority": "P1",
            "gold_blocker_class": "identity_core_verified_rank_only_blocker",
            "gold_blocker_domain": "rank_display",
            "gold_blocker_automation_path": "rank_display_gate_cleanup",
        },
    ])
    evidence = pd.DataFrame([
        {
            "server": 551,
            "rank": 8,
            "row_integrity_status": "ROW_VOTE_OUTSIDE_ALLOWED_SET",
            "row_integrity_reason": "ReOCR votes include text outside the allowed target set",
            "evidence_fragment_rows": 5,
            "evidence_verified_expected_targets": 5,
            "evidence_verified_observed_targets": 0,
            "evidence_unresolved_targets": 0,
            "evidence_field_mismatch_targets": 0,
            "evidence_vote_outside_allowed_targets": 2,
        }
    ])

    details, summary = _build_gold_core_blocker_report(triage, evidence)

    assert len(details) == 1
    assert details.loc[0, "rank"] == 8
    assert details.loc[0, "gold_core_failure_class"] == "vote_warning_gate_review"
    assert details.loc[0, "gold_core_fix_lane"] == "safe_warning_downgrade_candidate"
    assert summary.loc[0, "rows"] == 1


def test_gold_core_blocker_report_prioritizes_observed_text_confirmed_over_vote_noise():
    triage = pd.DataFrame([
        {
            "server": 551,
            "rank": 23,
            "gold_core_blocker": True,
            "gold_blocker_priority": "P2",
            "gold_blocker_class": "nonlocal_or_multilingual_player_display_drift",
            "gold_blocker_domain": "player_name",
            "gold_blocker_automation_path": "multilingual_name_ocr_or_conservative_block",
            "character_reocr_verified_expected": 0,
            "character_reocr_verified_observed": 1,
            "character_reocr_unresolved": 0,
            "character_reocr_skipped_nonlocal": 2,
        }
    ])
    evidence = pd.DataFrame([
        {
            "server": 551,
            "rank": 23,
            "row_integrity_status": "ROW_OBSERVED_TEXT_CONFIRMED",
            "row_integrity_reason": "ReOCR confirmed observed player-name glyphs instead of expected glyphs",
            "evidence_fragment_rows": 1,
            "evidence_verified_expected_targets": 0,
            "evidence_verified_observed_targets": 1,
            "evidence_unresolved_targets": 0,
            "evidence_field_mismatch_targets": 0,
            "evidence_vote_outside_allowed_targets": 1,
        }
    ])

    details, _ = _build_gold_core_blocker_report(triage, evidence)

    assert details.loc[0, "gold_core_failure_class"] == "observed_text_confirmed"
    assert details.loc[0, "gold_core_fix_lane"] == "manual_or_policy"
