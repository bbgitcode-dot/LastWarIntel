from services.import_repository import build_import_run_report


def test_ranking_guard_review_uses_visible_rank_from_screenshot_window():
    grouped = {
        (554, "total_hero_power"): [
            {"rank": 64, "power": 160_000_000, "source_file": "s.png"},
            {"rank": 65, "power": 159_000_000, "source_file": "s.png"},
            {"rank": 66, "power": 767_730_565, "source_file": "s.png"},
            {"rank": 67, "power": 156_000_000, "source_file": "s.png"},
            {"rank": 68, "power": 155_000_000, "source_file": "s.png"},
            {"rank": 69, "power": 154_000_000, "source_file": "s.png"},
            {"rank": 70, "power": 153_000_000, "source_file": "s.png"},
            {"rank": 71, "power": 152_000_000, "source_file": "s.png"},
            {"rank": 72, "power": 151_000_000, "source_file": "s.png"},
        ],
        ("REVIEW", "ranking_guard_quarantine"): [
            {
                "original_server": 554,
                "original_ranking_type": "total_hero_power",
                "expected_ranking_type": "total_hero_power",
                "rank": 3,
                "source_file": "s.png",
                "ranking_guard_warning": "power_sanity:power_recovery_candidates_ambiguous",
            }
        ],
    }
    report = build_import_run_report(grouped, screenshots=1, runtime_seconds=1.0, output_file="out.xlsx")
    review = report["reviews"][0]
    assert review["rank"] == 66
    assert review["visible_rank"] == 66
    assert review["raw_review_rank"] == 3
    assert review["screenshot_rank_window"]["start"] == 64
    assert review["screenshot_rank_window"]["end"] == 72
    assert report["recognition_quality"]["rank_trace_fixed_reviews"] == 1
