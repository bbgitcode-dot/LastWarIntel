import pandas as pd

from inference.context_engine import apply_contextual_inference
from ground_truth_validator import _apply_alignment_guard


def test_alignment_guard_suppresses_character_reocr_for_context_gap():
    detail = pd.DataFrame([
        {
            "server": 551,
            "rank": 20,
            "expected_power": 252808716,
            "match_method": "server_power",
            "failure_class": "matched",
            "valid_match": True,
            "bad_match": False,
            "power_match": True,
            "alliance_match": True,
            "name_normalized_match": True,
            "character_verification_candidate": False,
            "high_value_character_verification": False,
            "character_verification_reasons": "",
            "character_verification_targets": "[]",
            "player_name_character_verification_targets": "[]",
            "alliance_tag_character_verification_targets": "[]",
            "character_reocr_status": "not_requested",
            "character_reocr_targets": 0,
            "character_reocr_verified_expected": 0,
            "character_reocr_verified_observed": 0,
            "character_reocr_unresolved": 0,
            "character_reocr_evidence": "[]",
            "gold_fidelity_blocker": False,
            "identity_risk": False,
            "identity_risk_reasons": "",
            "high_value_identity_risk": False,
        },
        {
            "server": 551,
            "rank": 21,
            "expected_power": 250009089,
            "match_method": "inference_context_gap",
            "failure_class": "inferred_context_gap",
            "valid_match": True,
            "bad_match": False,
            "power_match": False,
            "alliance_match": False,
            "name_normalized_match": False,
            "character_verification_candidate": True,
            "high_value_character_verification": True,
            "character_verification_reasons": "display_character_difference",
            "character_verification_targets": '[{"field":"player_name","position":0,"expected":"K","observed":"Y"}]',
            "player_name_character_verification_targets": '[{"field":"player_name","position":0,"expected":"K","observed":"Y"}]',
            "alliance_tag_character_verification_targets": "[]",
            "character_reocr_status": "mixed",
            "character_reocr_targets": 1,
            "character_reocr_verified_expected": 0,
            "character_reocr_verified_observed": 0,
            "character_reocr_unresolved": 1,
            "character_reocr_evidence": '[{"status":"unresolved"}]',
            "gold_fidelity_blocker": True,
            "identity_risk": True,
            "identity_risk_reasons": "targeted_character_verification_required;gold_fidelity_blocker",
            "high_value_identity_risk": True,
        },
        {
            "server": 551,
            "rank": 22,
            "expected_power": 248671604,
            "match_method": "server_power",
            "failure_class": "matched",
            "valid_match": True,
            "bad_match": False,
            "power_match": True,
            "alliance_match": True,
            "name_normalized_match": True,
            "character_verification_candidate": False,
            "high_value_character_verification": False,
            "character_verification_reasons": "",
            "character_verification_targets": "[]",
            "player_name_character_verification_targets": "[]",
            "alliance_tag_character_verification_targets": "[]",
            "character_reocr_status": "not_requested",
            "character_reocr_targets": 0,
            "character_reocr_verified_expected": 0,
            "character_reocr_verified_observed": 0,
            "character_reocr_unresolved": 0,
            "character_reocr_evidence": "[]",
            "gold_fidelity_blocker": False,
            "identity_risk": False,
            "identity_risk_reasons": "",
            "high_value_identity_risk": False,
        },
    ])

    guarded = _apply_alignment_guard(detail)
    gap = guarded.loc[guarded["rank"] == 21].iloc[0]

    assert bool(gap["alignment_context_gap"]) is True
    assert bool(gap["alignment_safe_for_character_verification"]) is False
    assert bool(gap["character_verification_candidate"]) is False
    assert gap["character_verification_targets"] == "[]"
    assert gap["character_reocr_status"] == "not_requested_alignment_context_gap"
    assert gap["character_reocr_targets"] == 0
    assert bool(gap["gold_fidelity_blocker"]) is False
    assert gap["identity_risk_reasons"] == "alignment_context_gap"
