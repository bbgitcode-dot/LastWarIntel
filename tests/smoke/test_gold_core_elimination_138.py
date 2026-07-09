import pandas as pd

from ground_truth_validator import _apply_gold_core_elimination, _build_gold_core_elimination_report


def _base_row(**overrides):
    row = {
        "server": 551,
        "rank": 20,
        "expected_name": "Pumpkin G",
        "ocr_name": "Pumpkin 6",
        "expected_alliance_display": "IVE",
        "ocr_alliance_display": "IVE",
        "verified_name_display": "Pumpkin 6",
        "verified_alliance_display": "IVE",
        "display_reconstruction_status": "name_reconstructed",
        "display_reconstructed_name": "Pumpkin G",
        "display_reconstructed_alliance_tag": "IVE",
        "display_promotion_eligible": True,
        "display_promotion_block_reason": "",
        "display_confidence_decision": "eligible_high_confidence",
        "display_reconstruction_unresolved_targets": 0,
        "display_reconstruction_observed_votes": 0,
        "gold_core_blocker": True,
        "verified_core_identity_match": False,
        "verified_core_identity_resolution": False,
        "identity_policy_class": "full_display_required",
        "identity_risk_reasons": "player_name_display_drift;gold_fidelity_blocker",
        "match_method": "server_power",
        "bad_match": False,
        "power_match": True,
        "core_alliance_match": True,
        "alignment_context_gap": False,
    }
    row.update(overrides)
    return row


def test_gold_core_elimination_clears_only_strong_display_reconstruction():
    detail = pd.DataFrame([_base_row()])

    out = _apply_gold_core_elimination(detail)

    assert bool(out.loc[0, "gold_core_elimination_cleared"]) is True
    assert bool(out.loc[0, "gold_core_blocker"]) is False
    assert bool(out.loc[0, "verified_core_identity_match"]) is True
    assert out.loc[0, "identity_policy_class"] == "gold_core_eliminated_display_reconstruction"
    assert bool(out.loc[0, "gold_core_elimination_operational_truth_modified"]) is False


def test_gold_core_elimination_keeps_context_gap_read_only_blocked():
    detail = pd.DataFrame([
        _base_row(
            match_method="inference_context_gap",
            alignment_context_gap=True,
            display_reconstruction_status="contextual_display_suggestion",
            display_promotion_eligible=False,
            display_promotion_block_reason="context_gap_evidence_only",
        )
    ])

    out = _apply_gold_core_elimination(detail)

    assert bool(out.loc[0, "gold_core_elimination_cleared"]) is False
    assert bool(out.loc[0, "gold_core_blocker_after_elimination"]) is True
    assert out.loc[0, "gold_core_elimination_action"] == "keep_blocked"
    assert "context_gap" in out.loc[0, "gold_core_elimination_reason"]


def test_gold_core_elimination_report_summarizes_cleared_and_remaining():
    detail = pd.DataFrame([_base_row(), _base_row(rank=21, display_reconstructed_name="Wrong")])
    out = _apply_gold_core_elimination(detail)

    summary, rows = _build_gold_core_elimination_report(out)

    assert not rows.empty
    assert int(summary["cleared_rows"].sum()) == 1
    assert int(summary["remaining_blockers"].sum()) == 1
    assert rows["gold_core_elimination_operational_truth_modified"].eq(False).all()
