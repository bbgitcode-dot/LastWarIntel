import pandas as pd

from ground_truth_validator import (
    GOLD_ACCURACY_MODE,
    _apply_reocr_budget_gate,
    _scheduler_priority_from_budget,
)


class Target:
    def __init__(self, field, expected, observed, reason):
        self.field = field
        self.expected = expected
        self.observed = observed
        self.reason = reason


def test_gold_accuracy_mode_is_enabled_by_default():
    assert GOLD_ACCURACY_MODE is True


def test_gold_accuracy_mode_keeps_budget_skipped_targets():
    targets = [Target("alliance_tag", "b", "B", "case_sensitive_tag_difference")]
    kept, skipped, reasons = _apply_reocr_budget_gate(
        targets,
        raw_alliance_match=True,
        raw_alliance_case_sensitive_mismatch=True,
        raw_name_display_exact=True,
        raw_name_normalized_match=True,
        name_normalized_similarity=1.0,
        raw_power_match=True,
        pre_core_safe=True,
    )
    assert kept == targets
    assert skipped == 0
    assert "gold_accuracy_mode_budget_gate_disabled" in reasons


def test_gold_accuracy_scheduler_collects_low_value_evidence_instead_of_saving_runtime():
    decision = _scheduler_priority_from_budget(pd.Series({
        "evidence_budget_tier": "low",
        "evidence_budget_action": "block_early_or_reuse_cache",
        "evidence_budget_expected_cost_ms": 6500,
        "display_confidence_decision": "blocked_low_evidence",
        "display_reconstruction_status": "blocked_display_promotion",
        "evidence_priority_score": 0.31,
        "display_coverage_score": 0.08,
        "evidence_avg_fragment_confidence": 0.41,
        "evidence_unresolved_fragments": 2,
        "evidence_observed_fragments": 0,
        "alignment_context_gap": False,
        "display_promotion_eligible": False,
    }))
    assert decision["evidence_scheduler_decision"] == "schedule_accuracy_reocr"
    assert decision["scheduler_expected_runtime_ms"] == 6500
    assert decision["scheduler_estimated_saved_ms"] == 0
    assert decision["scheduler_accuracy_mode"] is True
