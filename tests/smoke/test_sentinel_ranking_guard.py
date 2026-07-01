import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from parser.ranking_guard import apply_ranking_guard, evaluate_ranking_row
from services.import_repository import build_import_run_report


def test_ranking_guard_quarantines_thp_row_inside_alliance_power():
    grouped = {
        (551, "alliance_power"): [
            {
                "rank": 1,
                "alliance_tag": "ABC",
                "player_name": "PlayerOne",
                "name": "[ABC] PlayerOne",
                "power": 987_654_321,
                "source_file": "thp_in_alliance.png",
            }
        ]
    }

    guarded = apply_ranking_guard(grouped)

    assert ("REVIEW", "ranking_guard_quarantine") not in guarded
    assert (551, "alliance_power") not in guarded or guarded[(551, "alliance_power")] == []
    recovered = guarded[(551, "total_hero_power")]
    assert len(recovered) == 1
    assert recovered[0]["original_ranking_type"] == "alliance_power"
    assert recovered[0]["ranking_type"] == "total_hero_power"
    assert recovered[0]["ranking_guard_status"] == "recovered"


def test_ranking_guard_quarantines_alliance_row_inside_total_hero_power():
    row = {
        "rank": 1,
        "name": "Very Strong Alliance",
        "player_name": "",
        "power": 42_000_000_000,
        "source_file": "alliance_in_thp.png",
    }

    decision = evaluate_ranking_row(row, "total_hero_power")

    assert decision.should_quarantine
    assert decision.expected_ranking_type == "alliance_power"
    assert "assigned_total_hero_power_but_row_is_alliance_shaped" in decision.reasons


def test_ranking_guard_keeps_valid_player_row():
    grouped = {
        (551, "total_hero_power"): [
            {
                "rank": 1,
                "alliance_tag": "ABC",
                "player_name": "PlayerOne",
                "name": "[ABC] PlayerOne",
                "power": 987_654_321,
                "source_file": "valid_thp.png",
            }
        ]
    }

    guarded = apply_ranking_guard(grouped)

    assert ("REVIEW", "ranking_guard_quarantine") not in guarded
    row = guarded[(551, "total_hero_power")][0]
    assert row["ranking_guard_status"] == "validated"


def test_import_report_surfaces_ranking_guard_quarantine():
    grouped = {
        ("REVIEW", "ranking_guard_quarantine"): [
            {
                "rank": 7,
                "original_server": 551,
                "ranking_type": "alliance_power",
                "original_ranking_type": "alliance_power",
                "expected_ranking_type": "total_hero_power",
                "ranking_guard_warning": "ranking_type_conflict:player_alliance_tag_shape",
                "source_file": "mixed.png",
            }
        ]
    }

    report = build_import_run_report(grouped, screenshots=1, runtime_seconds=1.0, output_file="out.xlsx")

    assert report["status"] == "Review"
    assert report["review_count"] == 1
    assert report["imports"][0]["status"] == "Quarantine"
    assert report["reviews"][0]["title"] == "Ranking Guard quarantine"
    assert report["reviews"][0]["reason"] == "ranking_guard_quarantine"
