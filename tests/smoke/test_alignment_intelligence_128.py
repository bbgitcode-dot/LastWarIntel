import pandas as pd

from ground_truth_validator import _apply_alignment_guard


def test_alignment_intelligence_allows_read_only_evidence_for_high_confidence_context_gap():
    detail = pd.DataFrame([
        {
            "server": 551,
            "rank": 21,
            "match_method": "inference_context_gap",
            "failure_class": "inferred_context_gap",
            "inference_status": "accepted",
            "inference_evidence": "rank_between_trusted_neighbors;tight_bounded_gap;expected_power_fits_neighbor_trend;gap_marked_recoverable_by_validator;unsafe_row_match_blocked",
            "gap_recoverable": True,
            "gap_reason": "bounded_gap",
            "power_similarity": 0.9947,
            "character_verification_candidate": True,
            "high_value_character_verification": True,
            "character_verification_reasons": "display_character_difference",
            "character_verification_targets": "[]",
            "player_name_character_verification_targets": "[]",
            "alliance_tag_character_verification_targets": "[]",
            "character_reocr_status": "not_requested",
            "character_reocr_targets": 1,
            "character_reocr_verified_expected": 0,
            "character_reocr_verified_observed": 0,
            "character_reocr_unresolved": 0,
            "character_reocr_evidence": "[]",
            "gold_fidelity_blocker": True,
            "identity_risk": True,
            "identity_risk_reasons": "alignment_context_gap",
            "high_value_identity_risk": True,
        }
    ])

    guarded = _apply_alignment_guard(detail)
    row = guarded.iloc[0]

    assert row["alignment_context_gap"] is True or bool(row["alignment_context_gap"])
    assert row["alignment_guard_status"] == "context_gap_read_only_evidence_gate"
    assert row["alignment_score"] >= 0.9
    assert bool(row["verification_allowed_read_only"])
    assert row["read_only_verification_status"] == "eligible_not_executed_phase1"
    assert row["character_reocr_status"] == "not_executed_read_only_alignment_phase1"
    assert bool(row["gold_fidelity_blocker"]) is False


def test_normal_observed_row_keeps_operational_character_policy():
    detail = pd.DataFrame([
        {
            "server": 551,
            "rank": 1,
            "match_method": "server_power",
            "failure_class": "matched",
            "inference_status": "not_evaluated",
            "inference_evidence": "",
            "gap_recoverable": False,
            "gap_reason": "",
            "power_similarity": 1.0,
            "character_verification_candidate": True,
            "high_value_character_verification": True,
            "character_verification_reasons": "same_confusion_family_difference",
            "character_verification_targets": "[]",
            "player_name_character_verification_targets": "[]",
            "alliance_tag_character_verification_targets": "[]",
            "character_reocr_status": "verified_expected",
            "character_reocr_targets": 2,
            "character_reocr_verified_expected": 2,
            "character_reocr_verified_observed": 0,
            "character_reocr_unresolved": 0,
            "character_reocr_evidence": "[]",
            "gold_fidelity_blocker": False,
            "identity_risk": True,
            "identity_risk_reasons": "gold_fidelity_blocker",
            "high_value_identity_risk": True,
        }
    ])

    guarded = _apply_alignment_guard(detail)
    row = guarded.iloc[0]

    assert row["alignment_guard_status"] == "row_alignment_observed"
    assert bool(row["alignment_safe_for_character_verification"])
    assert not bool(row["verification_allowed_read_only"])
    assert row["verification_block_reason"] == "normal_row_character_verification_policy"
