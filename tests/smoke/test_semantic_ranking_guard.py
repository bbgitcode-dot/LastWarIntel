from parser.ranking_guard import apply_ranking_guard, evaluate_ranking_row
from parser.server import detect_ranking_type


def test_german_column_header_detects_alliance_power():
    assert detect_ranking_type("Rang Allianzname Kampfkraft") == "alliance_power"


def test_german_column_header_detects_total_hero_power():
    assert detect_ranking_type("Rang Kommandant Kampfkraft") == "total_hero_power"


def test_bracketed_alliance_name_is_not_player_evidence_in_alliance_power():
    grouped = {
        (552, "alliance_power"): [
            {
                "rank": 26,
                "name": "[drr] Young Tokai Teio",
                "power": 896_061_016,
                "raw_text": "26 | [drr] Young Tokai Teio | Kriegszone #552 | 896.061.016",
            }
        ]
    }

    guarded = apply_ranking_guard(grouped)

    assert ("REVIEW", "ranking_guard_quarantine") not in guarded
    assert guarded[(552, "alliance_power")][0]["ranking_guard_status"] == "validated"


def test_explicit_player_fields_still_quarantine_inside_alliance_power():
    row = {
        "rank": 1,
        "alliance_tag": "ABC",
        "player_name": "PlayerOne",
        "name": "[ABC] PlayerOne",
        "power": 987_654_321,
        "source_file": "thp_in_alliance.png",
    }

    decision = evaluate_ranking_row(row, "alliance_power")

    assert decision.should_quarantine
    assert decision.expected_ranking_type == "total_hero_power"
    assert "assigned_alliance_power_but_row_is_thp_shaped" in decision.reasons
