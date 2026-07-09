import pandas as pd

from ground_truth_validator import _reconstruct_display_row


def test_display_reconstruction_guard_blocks_unknown_name_base():
    row = pd.Series({
        "expected_name": "GD VIP 지디",
        "expected_alliance_display": "IVE",
        "ocr_name": "UNKNOWN",
        "ocr_alliance_display": "",
        "verified_name_display": "UNKNOWN",
        "verified_alliance_display": "IVE",
        "character_reocr_evidence": '[{"field":"player_name","position":0,"expected":"G","status":"verified_expected","confidence":1.0},{"field":"player_name","position":4,"expected":"I","status":"verified_expected","confidence":1.0},{"field":"alliance_tag","position":0,"expected":"I","status":"verified_expected","confidence":1.0},{"field":"alliance_tag","position":1,"expected":"V","status":"verified_expected","confidence":1.0},{"field":"alliance_tag","position":2,"expected":"E","status":"verified_expected","confidence":1.0}]',
        "read_only_reocr_evidence": "[]",
    })

    out = _reconstruct_display_row(row)

    assert out["display_reconstructed_name"] == "UNKNOWN"
    assert out["display_reconstructed_alliance_tag"] == "IVE"
    assert out["display_reconstruction_status"] == "alliance_reconstructed_name_blocked"
    assert out["display_promotion_eligible"] is False
    assert "blocked_unknown_base" in out["display_promotion_block_reason"]
    assert out["display_reconstruction_operational_truth_modified"] is False


def test_display_reconstruction_guard_allows_full_safe_reconstruction():
    row = pd.Series({
        "expected_name": "Pumpkin G",
        "expected_alliance_display": "IVE",
        "ocr_name": "Pumpkin 6",
        "ocr_alliance_display": "IVE",
        "verified_name_display": "Pumpkin G",
        "verified_alliance_display": "IVE",
        "character_reocr_evidence": '[{"field":"player_name","position":8,"expected":"G","status":"verified_expected","confidence":1.0}]',
        "read_only_reocr_evidence": "[]",
    })

    out = _reconstruct_display_row(row)

    assert out["display_reconstructed_name"] == "Pumpkin G"
    assert out["display_reconstruction_status"] in {"full_display_reconstructed", "name_reconstructed"}
    assert out["display_promotion_eligible"] is True
    assert out["display_promotion_block_reason"] == ""
