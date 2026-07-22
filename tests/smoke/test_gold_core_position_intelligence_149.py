import json
import pandas as pd

from ground_truth_validator import _build_gold_core_character_evidence_map


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
            {"field": "player_name", "position": 1, "expected": "D", "selected": "D", "status": "verified_expected", "confidence": 0.93, "screenshot": "thp_07.png"},
            {"field": "player_name", "position": 6, "expected": "0", "selected": "y", "status": "verified_observed", "confidence": 0.88, "screenshot": "thp_07.png"},
        ]),
    }
    data.update(overrides)
    return data


def test_position_map_exposes_blocking_positions_without_clearance():
    cases, positions, heatmap = _build_gold_core_character_evidence_map(pd.DataFrame([_row()]))
    assert len(cases) == 1
    assert len(positions) == len("JDubbz04")
    assert bool(positions["operational_truth_modified"].any()) is False
    assert set(positions["position_status"]).issubset({"CONFIRMED", "MISSING", "CONFLICT", "UNRESOLVED"})
    assert int(cases.iloc[0]["positions_conflicting"]) >= 1
    assert cases.iloc[0]["recommended_evidence_action"] == "resolve_conflict"
    assert not heatmap.empty


def test_unknown_is_not_filled_from_ground_truth():
    cases, positions, _ = _build_gold_core_character_evidence_map(pd.DataFrame([_row(expected_name="ABC", ocr_name="UNKNOWN", display_reconstructed_name="UNKNOWN", character_reocr_evidence="[]")]))
    assert cases.iloc[0]["coverage"] == 0.0
    assert set(positions["position_status"]) == {"MISSING"}
    assert all(positions["proof_source"].astype(str) == "")
