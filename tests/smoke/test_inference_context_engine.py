import pandas as pd

from inference.context_engine import apply_contextual_inference


def test_context_engine_accepts_single_bounded_gap_without_changing_ocr_fields():
    detail = pd.DataFrame([
        {"server": 551, "rank": 35, "expected_power": 231359734, "ocr_power": 231359734, "power_match": True, "alliance_match": True, "name_normalized_match": True, "valid_match": True, "match_method": "server_power", "bad_match": False, "gap_recoverable": False},
        {"server": 551, "rank": 37, "expected_power": 231047233, "ocr_power": 228244396, "power_match": False, "alliance_match": False, "name_normalized_match": False, "valid_match": False, "match_method": "blocked_rank_fallback", "bad_match": False, "gap_recoverable": True},
        {"server": 551, "rank": 38, "expected_power": 230761273, "ocr_power": 230761273, "power_match": True, "alliance_match": True, "name_normalized_match": True, "valid_match": True, "match_method": "server_power", "bad_match": False, "gap_recoverable": False},
    ])

    result, inferences = apply_contextual_inference(detail)

    assert len(inferences) == 1
    assert result.loc[1, "match_method"] == "inference_context_gap"
    assert result.loc[1, "failure_class"] == "inferred_context_gap"
    assert result.loc[1, "ocr_power"] == 228244396
    assert result.loc[1, "inference_confidence"] >= 0.88


def test_context_engine_rejects_unbounded_gap():
    detail = pd.DataFrame([
        {"server": 551, "rank": 37, "expected_power": 231047233, "ocr_power": 228244396, "power_match": False, "alliance_match": False, "name_normalized_match": False, "valid_match": False, "match_method": "blocked_rank_fallback", "bad_match": False, "gap_recoverable": True},
    ])

    result, inferences = apply_contextual_inference(detail)

    assert inferences == []
    assert result.loc[0, "match_method"] == "blocked_rank_fallback"
    assert result.loc[0, "inference_status"] == "insufficient_anchors"
