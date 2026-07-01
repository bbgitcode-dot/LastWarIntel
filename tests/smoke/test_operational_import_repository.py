from services.import_repository import build_import_run_report


def test_import_run_report_groups_current_operational_data():
    grouped = {
        (551, "total_hero_power"): [
            {"rank": 1, "power": 100, "source_file": "a.png"},
            {"rank": 2, "power": 90, "source_file": "a.png"},
        ],
        (550, "alliance_power"): [
            {"rank": 1, "power": 1000, "source_file": "b.png"},
        ],
    }

    report = build_import_run_report(grouped, screenshots=2, runtime_seconds=12.5, output_file="output/x.xlsx")

    assert report["server_count"] == 2
    assert report["rows"] == 3
    assert report["status"] == "Ready"
    assert report["data_guard"]["status"] == "Healthy"


def test_import_run_report_surfaces_server_assignment_conflict():
    grouped = {
        (551, "total_hero_power"): [
            {
                "rank": 8,
                "power": 100,
                "source_file": "bad.png",
                "data_guard_conflict": True,
                "server_warning": "server_assignment_conflict:metadata=552:row=551",
            }
        ]
    }

    report = build_import_run_report(grouped, screenshots=1, runtime_seconds=1, output_file="output/x.xlsx")

    assert report["status"] == "Review"
    assert report["review_count"] == 1
    assert report["reviews"][0]["reason"] == "server_assignment_conflict"


def test_import_report_exposes_power_candidate_trace_and_aggregates_review_count():
    from services.import_repository import build_import_run_report

    grouped = {
        (553, "total_hero_power"): [
            {
                "rank": 85,
                "ocr_rank": 100,
                "name": "[SWSQ] Bubellee",
                "power": 164_292_586,
                "power_recovered_from": 764_292_586,
                "power_recovery_method": "total_hero_power_context_candidate_recovery",
                "power_recovery_status": "recovered",
                "power_sanity_confidence": 0.77,
                "power_candidate_count": 2,
                "power_candidate_best": 164_292_586,
                "power_candidate_best_score": 0.77,
                "power_candidate_second": 224_292_586,
                "power_candidate_second_score": 0.61,
                "power_candidate_margin": 0.16,
                "power_recovery_selected_reason": "selected_clear_candidate",
                "power_recovery_decision_strategy": "context_candidate_margin",
                "power_recovery_decision_version": "v0.9.5.49",
                "power_recovery_legacy_used": False,
                "power_recovery_candidates": [
                    {"value": 164_292_586, "score": 0.77, "reasons": ["fits_following_neighbour_order"]},
                    {"value": 224_292_586, "score": 0.61, "reasons": ["local_median_distance:0.250"]},
                ],
                "rank_warning": "ocr_rank_differs_from_power_rank:100!=85",
                "source_file": "553_late.png",
            }
        ]
    }

    report = build_import_run_report(
        grouped,
        screenshots=1,
        runtime_seconds=1.25,
        output_file="output/lastwar_export.xlsx",
    )

    assert report["review_count"] == 1
    assert report["import_review_count"] == 1
    assert report["review_item_count"] == 0
    assert report["status"] == "Review"
    assert report["power_recovery"]["candidate_traces"] == 1
    assert report["power_recovery"]["recovered"] == 1
    trace = report["power_recovery"]["traces"][0]
    assert trace["power_original"] == 764_292_586
    assert trace["power_selected"] == 164_292_586
    assert trace["best_candidate"] == 164_292_586
    assert trace["decision_strategy"] == "context_candidate_margin"
    assert trace["decision_version"] == "v0.9.5.49"
    assert trace["legacy_used"] is False
    assert trace["second_candidate"] == 224_292_586
    assert trace["margin"] == 0.16
