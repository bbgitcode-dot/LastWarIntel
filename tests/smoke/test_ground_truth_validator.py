from pathlib import Path
import pandas as pd

from ground_truth_validator import load_ground_truth, load_ocr_output, validate


def test_ground_truth_validator_matches_rows(tmp_path: Path):
    gt_path = tmp_path / "gt.xlsx"
    ocr_path = tmp_path / "ocr.xlsx"

    pd.DataFrame([
        {
            "Server": 551,
            "Rank": 1,
            "Alliance": "PbC",
            "HeroPower": 416693161,
            "TrueName": "Joncollins21",
            "Screenshot": "screen1.png",
        },
        {
            "Server": 551,
            "Rank": 2,
            "Alliance": "IVE",
            "HeroPower": 320306014,
            "TrueName": "MEITTü メ 메잇",
            "Screenshot": "screen1.png",
        },
    ]).to_excel(gt_path, index=False)

    pd.DataFrame([
        {
            "rank": 1,
            "server": 551,
            "alliance_tag": "PbC",
            "player_name": "Joncollins21",
            "power": 416693161,
        },
        {
            "rank": 2,
            "server": 551,
            "alliance_tag": "IVE",
            "player_name": "MEITTü メ 메잇",
            "power": 320306014,
        },
    ]).to_excel(ocr_path, sheet_name="551_total_hero_power", index=False)

    gt = load_ground_truth(gt_path)
    ocr = load_ocr_output(ocr_path)
    summary, detail, category = validate(gt, ocr)

    assert summary.ground_truth_rows == 2
    assert summary.matched_rows == 2
    assert summary.name_exact_matches == 2
    assert summary.alliance_matches == 2
    assert summary.power_matches == 2
    assert summary.usable_identity_matches == 2
    assert summary.score == 100.0
    assert "mixed_latin_cjk" in set(category["name_category"])


def test_ground_truth_validator_counts_normalized_alliance_matches(tmp_path: Path):
    gt_path = tmp_path / "gt.xlsx"
    ocr_path = tmp_path / "ocr.xlsx"

    pd.DataFrame([
        {
            "Server": 551,
            "Rank": 1,
            "Alliance": "PBC",
            "HeroPower": 416693161,
            "TrueName": "Joncollins21",
            "Screenshot": "screen1.png",
        }
    ]).to_excel(gt_path, index=False)

    pd.DataFrame([
        {
            "rank": 1,
            "server": 551,
            "alliance_tag": "PC",
            "player_name": "Joncollins21",
            "power": 416693161,
        }
    ]).to_excel(ocr_path, sheet_name="551_total_hero_power", index=False)

    gt = load_ground_truth(gt_path)
    ocr = load_ocr_output(ocr_path)
    summary, detail, _category = validate(gt, ocr)

    assert summary.alliance_matches == 1
    assert summary.alliance_exact_matches == 0
    assert summary.alliance_normalized_matches == 1
    assert summary.usable_identity_matches == 1
    assert detail.iloc[0]["ocr_alliance_normalized"] == "PBC"
