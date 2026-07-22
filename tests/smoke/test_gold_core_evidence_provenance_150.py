import json
import pandas as pd

from ground_truth_validator import (
    _build_gold_core_character_evidence_map,
    _build_gold_core_evidence_provenance,
)


def _row(**overrides):
    data = {
        "server": 551,
        "rank": 41,
        "expected_name": "JDubbz04",
        "ocr_name": "JQubbzoy",
        "display_reconstructed_name": "JQubbzoy",
        "verified_name_display": "",
        "gold_core_blocker": True,
        "gold_core_blocker_after_elimination": True,
        "gold_core_failure_class": "vote_warning_gate_review",
        "gold_core_fix_lane": "safe_warning_downgrade_candidate",
        "promotion_guard_primary_blocker": "name_exact",
        "character_reocr_evidence": json.dumps([
            {
                "field": "player_name", "position": 1, "expected": "D", "selected": "D",
                "status": "verified_expected", "confidence": 0.93,
                "screenshot": "thp_07.png", "crop_box": [10, 20, 30, 40],
                "crop_strategy": "position_bound", "crop_anchor_status": "ok",
                "crop_diagnostic": "", "vote_texts": ["D", "D"],
            },
            {
                "field": "player_name", "position": 6, "expected": "0", "selected": "y",
                "status": "ambiguous_vote", "confidence": 0.61,
                "screenshot": "thp_07.png", "crop_box": [50, 20, 70, 40],
                "crop_strategy": "position_bound", "crop_anchor_status": "ok",
                "crop_diagnostic": "vote_outside_allowed_set", "vote_texts": ["y", "0"],
            },
        ]),
    }
    data.update(overrides)
    return data


def test_provenance_identifies_first_failed_stage_and_keeps_truth_read_only():
    detail = pd.DataFrame([_row()])
    cases, positions, _ = _build_gold_core_character_evidence_map(detail)
    prov_cases, prov_positions, stages, summary = _build_gold_core_evidence_provenance(detail, cases, positions)

    blocked = prov_positions[prov_positions["position_human"] == 7].iloc[0]
    assert blocked["first_failed_stage"] == "vote_resolution"
    assert blocked["vote_status"] == "BLOCKED"
    assert blocked["promotion_guard_status"] == "BLOCKED_NAME_EXACT"
    assert blocked["ground_truth_used_as_evidence"] is False or bool(blocked["ground_truth_used_as_evidence"]) is False
    assert bool(prov_positions["operational_truth_modified"].any()) is False
    assert set(stages["stage"]) == {"screenshot", "crop", "ocr", "vote", "reconstruction", "promotion_guard"}
    assert not prov_cases.empty
    assert "vote_resolution" in set(summary["first_failed_stage"])


def test_missing_unknown_position_stops_at_acquisition():
    detail = pd.DataFrame([_row(
        expected_name="ABC",
        ocr_name="UNKNOWN",
        display_reconstructed_name="UNKNOWN",
        character_reocr_evidence="[]",
    )])
    cases, positions, _ = _build_gold_core_character_evidence_map(detail)
    _, prov_positions, _, summary = _build_gold_core_evidence_provenance(detail, cases, positions)
    assert set(prov_positions["first_failed_stage"]) == {"character_acquisition"}
    assert all(prov_positions["screenshot_status"] == "MISSING")
    assert all(prov_positions["ground_truth_used_as_evidence"] == False)  # noqa: E712
    assert summary.iloc[0]["recommended_action"] == "acquire_position_evidence"
