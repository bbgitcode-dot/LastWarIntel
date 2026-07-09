import pandas as pd

from ground_truth_validator import (
    _build_character_acquisition_report,
    _build_character_position_intelligence_report,
    _scheduler_priority_from_budget,
)


def test_character_position_intelligence_flags_weak_positions_and_scheduler_uses_it():
    detail = pd.DataFrame([
        {
            "server": 551,
            "rank": 8,
            "expected_name": "GD VIP 지디",
            "ocr_name": "UNKNOWN",
            "expected_alliance_display": "IVE",
            "ocr_alliance_display": "",
            "alignment_context_gap": False,
            "evidence_budget_tier": "low",
            "evidence_budget_action": "block_early_or_reuse_cache",
            "evidence_priority_score": 0.2,
            "evidence_budget_expected_cost_ms": 3000,
            "display_promotion_eligible": False,
            "display_coverage_score": 0.1,
            "evidence_avg_fragment_confidence": 0.2,
            "evidence_unresolved_fragments": 1,
            "evidence_observed_fragments": 0,
        }
    ])
    debug = pd.DataFrame([
        {
            "server": 551,
            "rank": 8,
            "target_field": "player_name",
            "target_position": 2,
            "target_expected": " ",
            "target_observed": "K",
            "target_status": "unresolved",
            "selected": "",
            "confidence": 0.05,
            "nonempty_vote_chars": "",
            "debug_read": "vote_outside_allowed_set",
            "crop_anchor_status": "field_mismatch",
            "crop_width": 12,
            "crop_height": 30,
        }
    ])
    _, rows, heatmap, detail = _build_character_acquisition_report(detail, debug)
    summary, positions, rank_rows, detail = _build_character_position_intelligence_report(rows, heatmap, detail)

    assert not summary.empty
    assert not positions.empty
    assert positions.loc[0, "position_intelligence_level"] in {"critical", "weak"}
    assert detail.loc[0, "character_position_action"] in {
        "forced_position_acquisition",
        "position_adaptive_multicrop_retry",
    }
    sched = _scheduler_priority_from_budget(detail.loc[0])
    assert sched["evidence_scheduler_decision"] in {
        "schedule_position_forced_acquisition",
        "schedule_position_adaptive_multicrop_retry",
    }
    assert sched["scheduler_operational_truth_modified"] is False


def test_character_position_intelligence_keeps_stable_positions_standard():
    detail = pd.DataFrame([{"server": 551, "rank": 1, "expected_name": "Joncollins21", "ocr_name": "Joncollinszl"}])
    debug = pd.DataFrame([
        {
            "server": 551,
            "rank": 1,
            "target_field": "player_name",
            "target_position": 10,
            "target_expected": "2",
            "target_observed": "z",
            "target_status": "verified_expected",
            "selected": "2",
            "confidence": 1.0,
            "nonempty_vote_chars": "2;2;2",
            "debug_read": "verified_expected",
            "crop_anchor_status": "anchor_seen",
            "crop_width": 20,
            "crop_height": 50,
        }
    ])
    _, rows, heatmap, detail = _build_character_acquisition_report(detail, debug)
    _, positions, _, detail = _build_character_position_intelligence_report(rows, heatmap, detail)
    assert positions.loc[0, "position_intelligence_level"] == "stable"
    assert detail.loc[0, "character_position_action"] == "standard_acquisition"
