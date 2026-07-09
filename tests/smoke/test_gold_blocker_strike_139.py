import pandas as pd

from ground_truth_validator import _apply_gold_core_elimination


def test_gold_blocker_strike_clears_single_latin_glyph_with_full_anchors():
    detail = pd.DataFrame([
        {
            "server": 551,
            "rank": 47,
            "gold_core_blocker": True,
            "match_method": "server_power",
            "bad_match": False,
            "alignment_context_gap": False,
            "power_match": True,
            "core_alliance_match": True,
            "expected_name": "Sc4rfac3",
            "display_reconstructed_name": "Scyrfac3",
            "expected_alliance_display": "PwW",
            "display_reconstructed_alliance_tag": "PwW",
            "display_promotion_eligible": True,
            "display_confidence_decision": "eligible",
            "display_reconstruction_status": "alliance_reconstructed",
            "display_reconstruction_unresolved_targets": 0,
            "display_reconstruction_observed_votes": 0,
            "identity_risk_reasons": "player_name_display_drift;gold_fidelity_blocker",
        }
    ])

    out = _apply_gold_core_elimination(detail)
    row = out.iloc[0]

    assert bool(row["gold_core_elimination_cleared"])
    assert row["gold_core_elimination_action"] == "clear_gold_core_blocker_strike_i"
    assert row["gold_core_blocker_after_elimination"] is False or not bool(row["gold_core_blocker_after_elimination"])
    assert bool(row["verified_core_identity_match"])
    assert row["gold_core_elimination_operational_truth_modified"] is False or not bool(row["gold_core_elimination_operational_truth_modified"])


def test_gold_blocker_strike_does_not_clear_context_gap():
    detail = pd.DataFrame([
        {
            "server": 551,
            "rank": 21,
            "gold_core_blocker": True,
            "match_method": "inference_context_gap",
            "bad_match": False,
            "alignment_context_gap": True,
            "power_match": True,
            "core_alliance_match": True,
            "expected_name": "K9 Thunder",
            "display_reconstructed_name": "K9 Thunder",
            "expected_alliance_display": "IVE",
            "display_reconstructed_alliance_tag": "IVE",
            "display_promotion_eligible": True,
            "display_confidence_decision": "eligible",
            "display_reconstruction_status": "full_display_reconstructed",
            "display_reconstruction_unresolved_targets": 0,
            "display_reconstruction_observed_votes": 0,
        }
    ])

    out = _apply_gold_core_elimination(detail)
    row = out.iloc[0]

    assert not bool(row["gold_core_elimination_cleared"])
    assert row["gold_core_elimination_action"] == "keep_blocked"
    assert row["gold_core_elimination_reason"] == "blocked_context_gap_read_only"
