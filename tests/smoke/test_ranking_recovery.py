from parser.ranking_guard import apply_ranking_guard
from parser.ranking_recovery import evaluate_ranking_recovery


def test_ranking_recovery_moves_explicit_thp_row_from_alliance_power():
    grouped = {
        (551, "alliance_power"): [
            {
                "rank": 1,
                "alliance_tag": "PBC",
                "player_name": "Joncollinszl",
                "name": "Joncollinszl",
                "power": 416_693_161,
                "hero_power": 416_693_161,
                "source_file": "thp.png",
            }
        ]
    }

    recovered = apply_ranking_guard(grouped)

    assert (551, "total_hero_power") in recovered
    assert ("REVIEW", "ranking_guard_quarantine") not in recovered
    row = recovered[(551, "total_hero_power")][0]
    assert row["ranking_guard_status"] == "recovered"
    assert row["ranking_recovery_status"] == "recovered"
    assert row["original_ranking_type"] == "alliance_power"


def test_ranking_recovery_calibrates_low_power_alliance_name_false_positive():
    grouped = {
        (551, "alliance_power"): [
            {
                "rank": 43,
                "name": "[IVE] Impact Vale Elite",
                "power": 3_070_261_980,
                "source_file": "alliance.png",
            }
        ]
    }

    recovered = apply_ranking_guard(grouped)

    assert (551, "alliance_power") in recovered
    assert ("REVIEW", "ranking_guard_quarantine") not in recovered
    row = recovered[(551, "alliance_power")][0]
    assert row["ranking_guard_status"] == "validated_after_recovery_calibration"
    assert row["ranking_recovery_status"] == "calibrated_pass"
    assert "no_explicit_player_fields" in row["ranking_recovery_reason"]


def test_ranking_recovery_keeps_ambiguous_rows_quarantined():
    decision = evaluate_ranking_recovery(
        {"rank": 1, "power": 123},
        assigned_ranking_type="alliance_power",
        expected_ranking_type="total_hero_power",
        guard_reasons=["player_scale_power"],
        guard_confidence=0.8,
    )

    assert decision.status == "quarantine"
