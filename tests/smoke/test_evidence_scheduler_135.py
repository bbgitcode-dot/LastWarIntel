import pandas as pd

from ground_truth_validator import (
    _attach_evidence_scheduler,
    _build_evidence_scheduler_report,
    _scheduler_priority_from_budget,
)


def test_gold_accuracy_scheduler_does_not_early_exit_low_budget_rows():
    row = pd.Series({
        "evidence_budget_tier": "low",
        "evidence_budget_action": "block_early_or_reuse_cache",
        "evidence_budget_expected_cost_ms": 6500,
        "display_confidence_decision": "blocked_low_evidence",
        "display_reconstruction_status": "blocked_display_promotion",
        "evidence_priority_score": 0.42,
        "display_coverage_score": 0.18,
        "evidence_avg_fragment_confidence": 0.49,
        "evidence_unresolved_fragments": 2,
        "evidence_observed_fragments": 0,
        "alignment_context_gap": False,
        "display_promotion_eligible": False,
    })
    decision = _scheduler_priority_from_budget(row)
    assert decision["evidence_scheduler_decision"] == "schedule_accuracy_reocr"
    assert decision["scheduler_expected_runtime_ms"] == 6500
    assert decision["scheduler_estimated_saved_ms"] == 0
    assert decision["scheduler_accuracy_mode"] is True
    assert decision["scheduler_operational_truth_modified"] is False


def test_scheduler_schedules_high_eligible_rows():
    row = pd.Series({
        "evidence_budget_tier": "high",
        "evidence_budget_action": "full_character_reocr_budget",
        "evidence_budget_expected_cost_ms": 12000,
        "display_confidence_decision": "eligible",
        "display_reconstruction_status": "full_display_reconstructed",
        "evidence_priority_score": 0.88,
        "display_coverage_score": 0.95,
        "evidence_avg_fragment_confidence": 0.93,
        "evidence_unresolved_fragments": 0,
        "evidence_observed_fragments": 0,
        "alignment_context_gap": False,
        "display_promotion_eligible": True,
    })
    decision = _scheduler_priority_from_budget(row)
    assert decision["scheduler_priority"] == "critical"
    assert decision["evidence_scheduler_decision"] == "schedule_full_reocr"
    assert decision["scheduler_expected_runtime_ms"] == 12000


def test_scheduler_report_summarizes_queue():
    detail = pd.DataFrame([
        {
            "server": 551,
            "rank": 1,
            "expected_name": "Joncollins21",
            "ocr_name": "Joncollinszl",
            "expected_alliance_display": "PbC",
            "ocr_alliance_display": "PBC",
            "display_reconstruction_status": "name_reconstructed",
            "display_confidence_decision": "eligible",
            "display_promotion_eligible": True,
            "evidence_priority_score": 0.88,
            "evidence_budget_tier": "high",
            "evidence_budget_action": "full_character_reocr_budget",
            "evidence_budget_reason": "high_priority_and_eligible_evidence",
            "evidence_budget_expected_cost_ms": 12000,
            "evidence_avg_fragment_confidence": 0.93,
            "display_coverage_score": 0.95,
            "evidence_fragments_total": 6,
            "evidence_unresolved_fragments": 0,
            "evidence_observed_fragments": 0,
            "alignment_context_gap": False,
            "gold_core_blocker": False,
        }
    ])
    scheduled = _attach_evidence_scheduler(detail)
    summary, rows = _build_evidence_scheduler_report(scheduled)
    assert not summary.empty
    assert not rows.empty
    assert rows.iloc[0]["evidence_scheduler_decision"] == "schedule_full_reocr"
    assert "scheduled_runtime_ms" in summary.columns
    assert bool(rows.iloc[0]["scheduler_accuracy_mode"]) is True
