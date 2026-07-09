import pandas as pd

from ground_truth_validator import _reconstruct_display_row, _build_evidence_confidence_report


def test_evidence_confidence_blocks_unknown_base_reconstruction():
    row = pd.Series({
        "expected_name": "GD VIP 지디",
        "expected_alliance_display": "IVE",
        "ocr_name": "UNKNOWN",
        "ocr_alliance_display": "",
        "verified_alliance_display": "IVE",
        "character_reocr_evidence": '[{"field":"player_name","position":0,"expected":"G","observed":"U","status":"verified_expected","selected":"G","confidence":1.0,"votes":[{"char":"G","confidence":0.9}],"crop_anchor_status":"text_without_anchor","crop_diagnostic":"vote_outside_allowed_set"}]',
        "read_only_reocr_evidence": "[]",
    })
    result = _reconstruct_display_row(row)
    assert result["display_promotion_eligible"] is False
    assert "blocked_unknown_base" in result["display_promotion_block_reason"]
    assert result["display_reconstructed_name"] == "UNKNOWN"
    assert "evidence_avg_fragment_confidence" in result
    assert "display_coverage_score" in result


def test_evidence_confidence_report_contains_decision_columns():
    detail = pd.DataFrame([
        {
            "server": 551,
            "rank": 1,
            "expected_name": "Joncollins21",
            "ocr_name": "Joncollinszl",
            "expected_alliance_display": "PbC",
            "ocr_alliance_display": "PBC",
            "display_reconstruction_status": "name_reconstructed",
            "display_reconstructed_name": "Joncollins21",
            "display_reconstructed_alliance_tag": "PBC",
            "display_promotion_eligible": True,
            "display_promotion_block_reason": "",
            "display_confidence_decision": "eligible",
            "evidence_fragments_total": 2,
            "evidence_confirmed_fragments": 2,
            "evidence_observed_fragments": 0,
            "evidence_unresolved_fragments": 0,
            "evidence_avg_fragment_confidence": 0.91,
            "display_name_coverage_score": 1.0,
            "display_alliance_coverage_score": 0.0,
            "display_coverage_score": 0.8,
            "evidence_avg_crop_quality": 0.8,
            "evidence_avg_ocr_confidence": 0.9,
            "evidence_avg_vote_consensus": 1.0,
            "evidence_avg_position_stability": 0.9,
            "evidence_avg_unicode_class": 1.0,
            "alignment_context_gap": False,
            "gold_core_blocker": False,
            "display_reconstruction_operational_truth_modified": False,
        }
    ])
    summary, rows = _build_evidence_confidence_report(detail)
    assert not summary.empty
    assert not rows.empty
    assert "avg_fragment_confidence" in summary.columns
    assert "display_confidence_decision" in rows.columns
