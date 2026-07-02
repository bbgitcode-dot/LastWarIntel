import json
from pathlib import Path

from services.command_center import generate_command_center


def test_generate_command_center_from_reports(tmp_path: Path):
    data = tmp_path / "data"
    bench = tmp_path / "benchmarks"
    output = tmp_path / "output"
    data.mkdir()
    bench.mkdir()
    (data / "latest_import_report.json").write_text(json.dumps({
        "status": "Review",
        "readiness": 50,
        "server_count": 2,
        "servers": [553, 554],
        "screenshots": 12,
        "runtime_seconds": 42.5,
        "rows": 120,
        "review_item_count": 1,
        "import_review_count": 1,
        "output_file": "output/lastwar_export.xlsx",
        "data_guard": {"status": "Warning"},
        "power_recovery": {"recovered": 3, "ambiguous": 1, "traces": [{
            "server": 553,
            "ranking_type": "total_hero_power",
            "rank": 17,
            "name": "ThorNord",
            "power_original": 793262033,
            "power_selected": 193262033,
            "status": "recovered",
            "confidence": 0.83,
            "decision_reason": "selected_clear_candidate",
        }]},
        "review_ocr": {"attempted": 2, "promoted": 0},
        "row_reconstruction": {"attempted": 1, "promoted": 1},
        "imports": [{
            "server": 553,
            "ranking_type": "total_hero_power",
            "rows": 91,
            "status": "Ready",
            "screenshots": 8,
            "power_recovery_count": 3,
            "power_ambiguous_count": 1,
        }],
        "reviews": [{
            "server": 554,
            "ranking_type": "total_hero_power",
            "rank": 9,
            "title": "Ranking Guard quarantine",
            "reason": "ranking_guard_quarantine",
            "description": "Needs review",
            "screenshot": "example.png",
        }],
    }), encoding="utf-8")
    (bench / "ground_truth_validation_report.json").write_text(json.dumps({
        "precision": 0.5,
        "recall": 1.0,
        "f1": 0.6667,
        "score": 71.94,
        "validation_server": 551,
        "validation_ranking_type": "total_hero_power",
    }), encoding="utf-8")
    (bench / "inference_report.json").write_text(json.dumps({"rows": [{"rank": 1}]}), encoding="utf-8")

    result = generate_command_center(
        output_dir=output,
        import_report_path=data / "latest_import_report.json",
        ground_truth_report_path=bench / "ground_truth_validation_report.json",
        inference_report_path=bench / "inference_report.json",
    )

    command_center = Path(result["command_center"])
    review_dashboard = Path(result["review_dashboard"])
    assert command_center.exists()
    assert review_dashboard.exists()
    html = command_center.read_text(encoding="utf-8")
    assert "Sentinel Command Center" in html
    assert "Server 553" in html
    assert "ThorNord" in html
    assert "Ground Truth" in html
    assert "Review Dashboard" in review_dashboard.read_text(encoding="utf-8")
