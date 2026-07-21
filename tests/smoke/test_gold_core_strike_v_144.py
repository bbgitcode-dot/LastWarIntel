from pathlib import Path
import json
import pandas as pd

from gold_core.quality_intelligence import (
    build_gold_core_case_explorer,
    build_gold_core_quality_intelligence,
)


def test_established_truth_chain_overrides_fallback_heuristic(tmp_path: Path):
    detail = pd.DataFrame([{
        "server": 551, "rank": 41, "expected_name": "JDubbz04", "ocr_name": "JDubbzO4",
        "gold_core_blocker_before_elimination": True,
        "gold_core_blocker_after_elimination": True,
        "gold_core_elimination_candidate": True,
        # This would previously bias the heuristic toward promotion_guard.
        "display_promotion_block_reason": "promotion blocked",
    }])
    blocker = pd.DataFrame([{
        "server": 551, "rank": 41,
        "gold_core_failure_class": "crop_geometry_problem",
        "gold_core_failure_domain": "crop_geometry",
        "gold_core_fix_lane": "crop_geometry",
        "gold_core_next_safe_action": "Fix player crop anchoring first.",
        "gold_blocker_priority": "P1",
    }])
    plan = pd.DataFrame([{
        "server": 551, "rank": 41,
        "gold_core_resolution_action": "P1_CROP_GEOMETRY_FIRST",
        "gold_core_resolution_lane": "crop_geometry",
        "gold_core_resolution_next_step": "Fix player/tag crop anchoring and field isolation.",
    }])
    _, rows, _ = build_gold_core_quality_intelligence(detail, tmp_path, blocker, plan)
    row = rows.iloc[0]
    assert row["classification_source"] == "established_gold_core_triage"
    assert row["failure_class"] == "crop_geometry_problem"
    assert row["root_cause"] == "crop_geometry"
    assert row["recommendation"] == "Fix player/tag crop anchoring and field isolation."
    assert float(row["root_cause_confidence"]) == 0.98


def test_case_explorer_links_reports_and_writes_casebook(tmp_path: Path):
    detail = pd.DataFrame([{
        "server": 551, "rank": 20, "expected_name": "N E R D", "ocr_name": "N E R O",
        "gold_core_blocker_before_elimination": True,
        "gold_core_blocker_after_elimination": True,
        "gold_core_elimination_candidate": True,
        "gold_core_failure_class": "local_glyph_solvable",
        "gold_core_failure_domain": "latin_local_glyph",
        "gold_core_fix_lane": "glyph_crop_refinement",
        "gold_core_next_safe_action": "Run tighter local glyph crop candidates.",
        "gold_blocker_priority": "P1",
    }])
    _, rows, memory = build_gold_core_quality_intelligence(detail, tmp_path)
    cases, actions, casebook = build_gold_core_case_explorer(rows, memory, tmp_path)
    assert cases.iloc[0]["case_id"] == "S551-R20"
    assert cases.iloc[0]["report_ocr_evidence"] == "ocr_evidence_report.json"
    assert int(actions.iloc[0]["affected_cases"]) == 1
    assert casebook.exists()
    assert "N E R D" in casebook.read_text(encoding="utf-8")
    payload = json.loads((tmp_path / "gold_core_case_explorer.json").read_text(encoding="utf-8"))
    assert payload["operational_truth_modified"] is False


def test_failure_memory_uses_stable_server_rank_case_id(tmp_path: Path):
    detail = pd.DataFrame([{
        "server": 551, "rank": 8, "expected_name": "GD VIP", "ocr_name": "GD VlP",
        "gold_core_blocker_before_elimination": True,
        "gold_core_blocker_after_elimination": True,
        "gold_core_elimination_candidate": True,
    }])
    _, _, memory1 = build_gold_core_quality_intelligence(detail, tmp_path)
    detail.loc[0, "expected_name"] = "GD VIP corrected display"
    _, _, memory2 = build_gold_core_quality_intelligence(detail, tmp_path)
    assert memory1.iloc[0]["case_id"] == "S551-R8"
    assert memory2.iloc[0]["case_id"] == "S551-R8"
    assert int(memory2.iloc[0]["times_seen"]) == 2
