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


def test_ground_truth_validator_scopes_precision_to_ground_truth_server(tmp_path: Path):
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

    with pd.ExcelWriter(ocr_path, engine="openpyxl") as writer:
        pd.DataFrame([
            {
                "rank": 1,
                "server": 551,
                "alliance_tag": "PBC",
                "player_name": "Joncollins21",
                "power": 416693161,
            }
        ]).to_excel(writer, sheet_name="551_total_hero_power", index=False)
        pd.DataFrame([
            {
                "rank": 1,
                "server": 550,
                "alliance_tag": "WARF",
                "player_name": "Other Server",
                "power": 194754417,
            }
        ]).to_excel(writer, sheet_name="550_total_hero_power", index=False)

    gt = load_ground_truth(gt_path)
    ocr = load_ocr_output(ocr_path)
    summary, _detail, _category = validate(gt, ocr)

    assert summary.ocr_total_rows == 2
    assert summary.ocr_scope_rows == 1
    assert summary.precision == 1.0
    assert summary.validation_server == 551


def test_ground_truth_validator_reports_ranking_guard_quarantine(tmp_path: Path):
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

    with pd.ExcelWriter(ocr_path, engine="openpyxl") as writer:
        pd.DataFrame([
            {
                "rank": 99,
                "server": 551,
                "alliance_tag": "XXX",
                "player_name": "Wrong Row",
                "power": 123456789,
            }
        ]).to_excel(writer, sheet_name="551_total_hero_power", index=False)
        pd.DataFrame([
            {
                "original_server": 551,
                "rank": 1,
                "name": "[PBC] Joncollins21",
                "power": 416693161,
                "source_file": "screen1.png",
                "ranking_guard_reason": "test quarantine",
            }
        ]).to_excel(writer, sheet_name="REVIEW_ranking_guard_quarantine", index=False)

    gt = load_ground_truth(gt_path)
    ocr = load_ocr_output(ocr_path)
    quarantine = __import__("ground_truth_validator").load_ranking_guard_quarantine(ocr_path)
    summary, detail, _category = validate(gt, ocr, quarantine)

    assert summary.matched_rows == 0
    assert summary.ground_truth_quarantined_rows == 1
    assert summary.quarantine_scope_rows == 1
    assert detail.iloc[0]["failure_class"] == "ranking_guard_quarantine"
    assert detail.iloc[0]["quarantine_power"] == 416693161


def test_ground_truth_validator_resolves_unique_power_gap(tmp_path: Path):
    gt_path = tmp_path / "gt.xlsx"
    ocr_path = tmp_path / "ocr.xlsx"

    pd.DataFrame([
        {"Server": 551, "Rank": 1, "Alliance": "PBC", "HeroPower": 416693161, "TrueName": "Anchor A", "Screenshot": "screen1.png"},
        {"Server": 551, "Rank": 2, "Alliance": "IVE", "HeroPower": 286697731, "TrueName": "GD VIP", "Screenshot": "screen1.png"},
        {"Server": 551, "Rank": 3, "Alliance": "PBC", "HeroPower": 272378748, "TrueName": "x Zed", "Screenshot": "screen1.png"},
    ]).to_excel(gt_path, index=False)

    pd.DataFrame([
        {"rank": 1, "server": 551, "alliance_tag": "PBC", "player_name": "Anchor A", "power": 416693161},
        {"rank": 2, "server": 551, "alliance_tag": "", "player_name": "UNKNOWN", "power": 286697731},
        {"rank": 3, "server": 551, "alliance_tag": "PBC", "player_name": "x Zed", "power": 272378748},
    ]).to_excel(ocr_path, sheet_name="551_total_hero_power", index=False)

    gt = load_ground_truth(gt_path)
    ocr = load_ocr_output(ocr_path)
    summary, detail, _category = validate(gt, ocr)

    resolved = detail[detail["match_method"] == "gap_same_server_exact_power"]
    assert summary.matched_rows == 3
    assert summary.gap_resolved_rows == 1
    assert summary.blocked_rank_fallbacks == 0
    assert len(resolved) == 1
    assert resolved.iloc[0]["expected_name"] == "GD VIP"
