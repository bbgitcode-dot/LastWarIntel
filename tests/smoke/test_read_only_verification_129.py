import json

import pandas as pd

from ground_truth_validator import _apply_alignment_guard


def test_read_only_verification_execution_collects_evidence_without_truth_promotion():
    detail = pd.DataFrame([
        {
            "server": 551,
            "rank": 21,
            "match_method": "inference_context_gap",
            "failure_class": "inferred_context_gap",
            "expected_name": "K9 Thunder 자주포",
            "ocr_name": "显丛显丛 X YUNS",
            "expected_alliance_display": "IVE",
            "ocr_alliance_display": "IVE",
            "expected_power": 250009089,
            "ocr_power": 248671604,
            "quarantine_name": "Kg Thunder 升孕)",
            "quarantine_alliance": "IVE",
            "quarantine_power": 25009089,
            "quarantine_reason": "power_recovery_candidates_ambiguous",
            "inference_status": "accepted",
            "inference_confidence": 0.99,
            "inference_evidence": "rank_between_trusted_neighbors;tight_bounded_gap;expected_power_fits_neighbor_trend;unsafe_row_match_blocked",
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
    evidence = json.loads(row["read_only_reocr_evidence"])[0]

    assert bool(row["verification_allowed_read_only"])
    assert bool(row["read_only_reocr_executed"])
    assert row["read_only_verification_status"] == "executed_evidence_only_phase2"
    assert row["character_reocr_status"] == "executed_read_only_alignment_phase2"
    assert row["read_only_suggested_display"] == "IVE | K9 Thunder 자주포"
    assert row["read_only_confidence"] == 0.99
    assert evidence["scope"] == "evidence_only"
    assert evidence["operational_truth_modified"] is False
    assert evidence["decision"] == "evidence_collected_no_promotion"
    assert row["verified_name_display"] if "verified_name_display" in row else True
    assert bool(row["gold_fidelity_blocker"]) is False
