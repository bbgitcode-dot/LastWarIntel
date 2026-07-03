from services.import_repository import build_import_run_report
from parser.ranking_power_sanity_guard import apply_ranking_power_sanity_guard


def test_import_report_exposes_runtime_and_recognition_quality_metrics():
    grouped = {
        (554, "total_hero_power"): [
            {"rank": 1, "name": "A", "power": 200_000_000, "power_sanity_status": "validated", "source_file": "a.png"},
            {"rank": 2, "name": "B", "power": 190_000_000, "power_recovered_from": 19_000_000, "power_recovery_status": "recovered", "power_sanity_status": "recovered", "power_candidate_count": 1, "power_candidate_best": 190_000_000, "source_file": "a.png"},
        ]
    }
    report = build_import_run_report(
        grouped,
        screenshots=1,
        runtime_seconds=10.0,
        output_file="out.xlsx",
        runtime_breakdown={"row_ocr": 7.5, "seconds_per_screenshot": 10.0},
    )

    assert report["schema"] == "sentinel.import_run.v5"
    assert report["runtime_breakdown"]["row_ocr"] == 7.5
    assert report["recognition_quality"]["version"] == "v0.9.5.86"
    assert report["recognition_quality"]["power_validated_rows"] == 1
    assert report["recognition_quality"]["runtime_breakdown"]["seconds_per_screenshot"] == 10.0
    assert "power_recovery_by_family" in report["recognition_quality"]
    assert "near_miss_ambiguous" in report["power_recovery"]


def test_guarded_alliance_explosion_candidate_can_promote_strong_order_consistent_case():
    grouped = {
        (552, "alliance_power"): [
            {"rank": 1, "name": "top", "power": 27_000_000_000, "source_file": "s.png"},
            {"rank": 2, "name": "prior", "power": 24_000_000_000, "source_file": "s.png"},
            {"rank": 3, "name": "bad", "power": 79_085_297_891, "source_file": "s.png"},
            {"rank": 4, "name": "next", "power": 22_000_000_000, "source_file": "s.png"},
            {"rank": 5, "name": "tail", "power": 20_000_000_000, "source_file": "s.png"},
        ]
    }

    guarded = apply_ranking_power_sanity_guard(grouped)
    rows = guarded[(552, "alliance_power")]
    recovered = [row for row in rows if row.get("name") == "bad"]

    assert recovered
    assert recovered[0]["power"] == 22_085_297_891
    assert recovered[0]["power_recovery_status"] == "recovered"
    assert ("REVIEW", "ranking_guard_quarantine") not in guarded


def test_near_miss_low_truncation_promotes_order_consistent_clear_margin_case():
    grouped = {
        (551, "total_hero_power"): [
            {"rank": 1, "ocr_rank": 1, "name": "top", "power": 320_000_000, "source_file": "s.png"},
            {"rank": 2, "ocr_rank": 2, "name": "near miss", "power": 23_095_610, "source_file": "s.png"},
            {"rank": 3, "ocr_rank": 3, "name": "next", "power": 220_000_000, "source_file": "s.png"},
            {"rank": 4, "ocr_rank": 4, "name": "tail", "power": 210_000_000, "source_file": "s.png"},
        ]
    }

    guarded = apply_ranking_power_sanity_guard(grouped)
    rows = guarded[(551, "total_hero_power")]
    recovered = [row for row in rows if row.get("name") == "near miss"]

    assert recovered
    assert recovered[0]["power"] == 230_956_100
    assert recovered[0]["power_recovery_status"] == "recovered"
    assert recovered[0]["power_recovery_decision_version"] == "v0.9.5.86"
    assert recovered[0]["power_candidate_margin"] >= 0.03
