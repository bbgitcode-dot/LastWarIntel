from pathlib import Path

import pandas as pd

from ground_truth_validator import load_ground_truth, load_ocr_output, validate
from parser.character_verification import analyze_player_name_characters, analyze_alliance_tag_characters


def test_character_verification_finds_joncollins_21_vs_zl():
    plan = analyze_player_name_characters("Joncollins21", "Joncollinszl")
    assert plan.required is True
    assert "same_confusion_family_difference" in plan.reasons
    targets = [(f.position, f.expected, f.observed, f.group) for f in plan.findings]
    assert (10, "2", "z", "2zZ") in targets
    assert (11, "1", "l", "1lI|") in targets


def test_alliance_tag_verification_is_case_sensitive():
    plan = analyze_alliance_tag_characters("PbC", "PBC")
    assert plan.required is True
    assert "case_sensitive_tag_difference" in plan.reasons
    assert [(f.position, f.expected, f.observed) for f in plan.findings] == [(1, "b", "B")]


def test_validator_exports_character_verification_candidates(tmp_path: Path):
    gt_path = tmp_path / "gt.xlsx"
    ocr_path = tmp_path / "ocr.xlsx"

    pd.DataFrame([
        {"server": 551, "rank": 1, "alliance": "PbC", "power": 416693161, "true_name": "Joncollins21"},
    ]).to_excel(gt_path, index=False)

    pd.DataFrame([
        {"server": 551, "rank": 1, "alliance": "PBC", "power": 416693161, "player_name": "Joncollinszl"},
    ]).to_excel(ocr_path, sheet_name="551_total_hero_power", index=False)

    summary, detail, _category = validate(load_ground_truth(gt_path), load_ocr_output(ocr_path))

    assert summary.character_verification_candidate_rows == 1
    assert summary.high_value_character_verification_rows == 1
    assert summary.player_name_confusable_drift_rows == 1
    assert summary.alliance_tag_character_verification_rows == 1
    row = detail.iloc[0]
    assert row["character_verification_candidate"] is True or row["character_verification_candidate"] == True
    assert "targeted_character_verification_required" in row["identity_risk_reasons"]
    assert '"observed": "z"' in row["player_name_character_verification_targets"]
    assert '"reason": "case_sensitive_tag_difference"' in row["alliance_tag_character_verification_targets"]
