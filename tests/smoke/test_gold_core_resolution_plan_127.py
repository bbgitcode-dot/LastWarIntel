import pandas as pd

from ground_truth_validator import _build_gold_core_resolution_plan_report


def test_gold_core_resolution_plan_marks_safe_vote_warning_candidate():
    blockers = pd.DataFrame([
        {
            "server": 551,
            "rank": 8,
            "gold_blocker_priority": "P1",
            "gold_core_failure_class": "vote_warning_gate_review",
            "row_integrity_status": "ROW_VOTE_OUTSIDE_ALLOWED_SET",
            "verified_core_identity_match": True,
            "evidence_verified_expected_targets": 5,
            "evidence_verified_observed_targets": 0,
            "evidence_unresolved_targets": 0,
            "evidence_field_mismatch_targets": 0,
            "evidence_vote_outside_allowed_targets": 2,
        }
    ])

    details, summary = _build_gold_core_resolution_plan_report(blockers)

    assert details.loc[0, "gold_core_resolution_action"] == "P1_WARNING_DOWNGRADE_SAFE"
    assert details.loc[0, "gold_core_local_automation_candidate"] is True or bool(details.loc[0, "gold_core_local_automation_candidate"])
    assert summary.loc[0, "automation_candidate_rows"] == 1


def test_gold_core_resolution_plan_keeps_crop_geometry_blocked():
    blockers = pd.DataFrame([
        {
            "server": 551,
            "rank": 39,
            "gold_blocker_priority": "P2",
            "gold_core_failure_class": "crop_geometry_problem",
            "row_integrity_status": "ROW_FIELD_MISMATCH_DIAGNOSTIC",
            "verified_core_identity_match": False,
            "evidence_verified_expected_targets": 1,
            "evidence_verified_observed_targets": 0,
            "evidence_unresolved_targets": 0,
            "evidence_field_mismatch_targets": 1,
        }
    ])

    details, _ = _build_gold_core_resolution_plan_report(blockers)

    assert details.loc[0, "gold_core_resolution_action"] == "P1_CROP_GEOMETRY_FIRST"
    assert not bool(details.loc[0, "gold_core_local_automation_candidate"])


def test_gold_core_resolution_plan_requires_policy_for_nonlocal_script():
    blockers = pd.DataFrame([
        {
            "server": 551,
            "rank": 2,
            "gold_blocker_priority": "P1",
            "gold_core_failure_class": "policy_nonlocal_script_display",
            "row_integrity_status": "ROW_POLICY_NONLOCAL_REVIEW",
            "character_reocr_skipped_nonlocal": 5,
        }
    ])

    details, _ = _build_gold_core_resolution_plan_report(blockers)

    assert details.loc[0, "gold_core_resolution_action"] == "P2_SCRIPT_POLICY_REQUIRED"
    assert details.loc[0, "gold_core_resolution_lane"] == "script_display_policy"
