import pandas as pd

from ground_truth_validator import (
    _build_evidence_budget_report,
    _evidence_budget_decision,
    _reconstruct_display_row,
)


def test_evidence_budget_blocks_low_coverage_unknown_base():
    row = pd.Series({
        "rank": 8,
        "alignment_score": 0.6,
        "power_similarity": 1.0,
        "gold_core_blocker": True,
        "alignment_context_gap": False,
        "expected_name": "GD VIP 지디",
        "expected_alliance_display": "IVE",
        "ocr_name": "UNKNOWN",
        "ocr_alliance_display": "",
        "verified_alliance_display": "IVE",
        "character_reocr_evidence": '[{"field":"player_name","position":0,"expected":"G","observed":"U","status":"verified_expected","selected":"G","confidence":0.3,"votes":[{"char":"G","confidence":0.1},{"char":"U","confidence":0.1}],"crop_anchor_status":"text_without_anchor","crop_diagnostic":"vote_outside_allowed_set"}]',
        "read_only_reocr_evidence": "[]",
    })
    result = _reconstruct_display_row(row)
    assert result["display_promotion_eligible"] is False
    assert result["evidence_budget_action"] in {"block_early_or_reuse_cache", "cache_or_limited_retry"}
    assert result["evidence_budget_operational_truth_modified"] is False


def test_evidence_budget_high_priority_for_eligible_fragment():
    evidence = {
        "evidence_avg_fragment_confidence": 0.95,
        "display_coverage_score": 0.9,
        "evidence_fragments_total": 6,
        "evidence_unresolved_fragments": 0,
        "evidence_observed_fragments": 0,
        "display_confidence_decision": "eligible",
    }
    row = pd.Series({"rank": 4, "alignment_score": 0.9, "power_similarity": 1.0, "gold_core_blocker": False, "alignment_context_gap": False})
    decision = _evidence_budget_decision(row, evidence, "full_display_reconstructed")
    assert decision["evidence_budget_tier"] == "high"
    assert decision["evidence_budget_action"] == "full_character_reocr_budget"
    assert decision["evidence_priority_score"] >= 0.7


def test_evidence_budget_report_summarizes_actions():
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
            "evidence_priority_score": 0.82,
            "evidence_budget_tier": "high",
            "evidence_budget_action": "full_character_reocr_budget",
            "evidence_budget_reason": "high_priority_and_eligible_evidence",
            "evidence_budget_expected_cost_ms": 12000,
            "evidence_avg_fragment_confidence": 0.91,
            "display_coverage_score": 0.8,
            "display_name_coverage_score": 1.0,
            "display_alliance_coverage_score": 0.0,
            "evidence_fragments_total": 2,
            "evidence_unresolved_fragments": 0,
            "evidence_observed_fragments": 0,
            "alignment_context_gap": False,
            "gold_core_blocker": False,
            "evidence_budget_operational_truth_modified": False,
        }
    ])
    summary, rows = _build_evidence_budget_report(detail)
    assert not summary.empty
    assert not rows.empty
    assert "expected_cost_ms" in summary.columns
    assert rows.iloc[0]["evidence_budget_action"] == "full_character_reocr_budget"
