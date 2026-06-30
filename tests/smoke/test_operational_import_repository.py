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
