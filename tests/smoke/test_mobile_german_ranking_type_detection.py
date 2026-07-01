from parser.server import detect_ranking_type
from parser.ranking_guard import apply_ranking_guard


def test_detects_german_alliance_power_title():
    assert detect_ranking_type("Allianz-Kampfkraft") == "alliance_power"


def test_detects_german_total_hero_power_title():
    assert detect_ranking_type("Gesamtkampfkraft der Helden") == "total_hero_power"


def test_low_power_alliance_rows_from_alliance_screen_are_not_reclassified_as_thp():
    grouped = {
        (552, "alliance_power"): [
            {
                "rank": 26,
                "name": "[drr] Young Tokai Teio",
                "power": 896_061_016,
                "raw_text": "26 | [drr] Young Tokai Teio | Kriegszone #552 | 896.061.016",
            },
            {
                "rank": 27,
                "name": "[pipz] OPAぴっぴす",
                "power": 880_224_595,
                "raw_text": "27 | [pipz] OPAぴっぴす | Kriegszone #552 | 880.224.595",
            },
        ]
    }

    guarded = apply_ranking_guard(grouped)

    assert len(guarded[(552, "alliance_power")]) == 2
    assert ("REVIEW", "ranking_guard_quarantine") not in guarded
    assert all(row["ranking_guard_status"] == "validated" for row in guarded[(552, "alliance_power")])
