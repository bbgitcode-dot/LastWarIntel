from pathlib import Path

import pandas as pd

from ground_truth_validator import load_ground_truth, load_ocr_output, validate


def test_validator_separates_fuzzy_match_from_exact_identity(tmp_path: Path):
    gt_path = tmp_path / "gt.xlsx"
    ocr_path = tmp_path / "ocr.xlsx"

    pd.DataFrame([
        {"server": 551, "rank": 1, "alliance": "PBC", "power": 416693161, "true_name": "Joncollins21"},
    ]).to_excel(gt_path, index=False)

    pd.DataFrame([
        {"server": 551, "rank": 1, "alliance": "PBC", "power": 416693161, "player_name": "Joncollinszl"},
    ]).to_excel(ocr_path, sheet_name="551_total_hero_power", index=False)

    summary, detail, _category = validate(load_ground_truth(gt_path), load_ocr_output(ocr_path))

    assert summary.matched_rows == 1
    assert summary.usable_identity_matches == 1
    assert summary.player_name_display_exact_matches == 0
    assert summary.exact_identity_matches == 0
    assert summary.identity_risk_rows == 1
    assert summary.high_value_identity_risk_rows == 1
    assert summary.identity_fidelity_score == 0.0
    assert "player_name_display_drift" in detail.iloc[0]["identity_risk_reasons"]
    assert "fuzzy_or_normalized_identity_not_exact" in detail.iloc[0]["identity_risk_reasons"]


def test_validator_flags_case_sensitive_alliance_tag_drift(tmp_path: Path):
    gt_path = tmp_path / "gt.xlsx"
    ocr_path = tmp_path / "ocr.xlsx"

    pd.DataFrame([
        {"server": 551, "rank": 1, "alliance": "daY", "power": 123456789, "true_name": "PlayerOne"},
    ]).to_excel(gt_path, index=False)

    pd.DataFrame([
        {"server": 551, "rank": 1, "alliance": "DAY", "power": 123456789, "player_name": "PlayerOne"},
    ]).to_excel(ocr_path, sheet_name="551_total_hero_power", index=False)

    summary, detail, _category = validate(load_ground_truth(gt_path), load_ocr_output(ocr_path))

    assert summary.matched_rows == 1
    assert summary.alliance_matches == 1
    assert summary.alliance_tag_display_exact_matches == 0
    assert summary.alliance_tag_case_sensitive_mismatches == 1
    assert summary.exact_identity_matches == 0
    assert summary.identity_risk_rows == 1
    assert "alliance_tag_case_sensitive_mismatch" in detail.iloc[0]["identity_risk_reasons"]
