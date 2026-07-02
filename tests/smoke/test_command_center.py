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
            "source_file": "example.png",
            "best_candidate": 193262033,
            "second_candidate": 190262033,
            "best_score": 0.83,
            "second_score": 0.70,
            "margin": 0.13,
            "candidates": [{"value": 193262033, "score": 0.83, "reasons": ["ocr_error_model"]}],
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
    evidence_pack = Path(result["review_evidence_pack"])
    evidence_json = Path(result["review_evidence_json"])
    assert command_center.exists()
    assert review_dashboard.exists()
    assert evidence_pack.exists()
    assert evidence_json.exists()
    html = command_center.read_text(encoding="utf-8")
    assert "Sentinel Command Center" in html
    assert "Server 553" in html
    assert "ThorNord" in html
    assert "Ground Truth" in html
    assert "Review Dashboard" in review_dashboard.read_text(encoding="utf-8")
    evidence_html = evidence_pack.read_text(encoding="utf-8")
    assert "Sentinel Review Evidence Pack" in evidence_html
    assert "Suggested action" in evidence_html
    payload = json.loads(evidence_json.read_text(encoding="utf-8"))
    assert payload["schema"] == "sentinel.review_evidence_pack.v1"
    assert payload["items"][0]["id"] == "REV-001"



def test_review_evidence_binds_quarantine_trace_by_screenshot_and_margin(tmp_path: Path):
    data = tmp_path / "data"
    output = tmp_path / "output"
    data.mkdir()
    (data / "latest_import_report.json").write_text(json.dumps({
        "status": "Review",
        "readiness": 50,
        "review_item_count": 1,
        "power_recovery": {"recovered": 0, "ambiguous": 1, "traces": [{
            "server": None,
            "ranking_type": "ranking_guard_quarantine",
            "rank": 3,
            "source_file": "Screenshot_20260702-082210.png",
            "name": "[MBM] yochic",
            "power_original": 767730565,
            "power_selected": 767730565,
            "status": "ambiguous",
            "best_candidate": 167730565,
            "second_candidate": 159730565,
            "best_score": 0.7124,
            "second_score": 0.6939,
            "margin": 0.0185,
            "candidate_count": 2,
            "decision_reason": "quarantined_ambiguous_candidates",
            "candidates": [
                {"value": 167730565, "score": 0.7124, "digit_preservation_score": 0.3289, "reasons": ["ocr_error_model"]},
                {"value": 159730565, "score": 0.6939, "digit_preservation_score": 0.2578, "reasons": ["source_local_bucket_match"]},
            ],
        }]},
        "reviews": [{
            "server": 554,
            "ranking_type": "total_hero_power",
            "expected_ranking_type": "total_hero_power",
            "rank": 3,
            "title": "Ranking Guard quarantine",
            "reason": "ranking_guard_quarantine",
            "description": "power_sanity:power_recovery_candidates_ambiguous;ambiguous_candidates:best=0.712;margin=0.019",
            "screenshot": "Screenshot_20260702-082210.png",
        }],
    }), encoding="utf-8")

    result = generate_command_center(
        output_dir=output,
        import_report_path=data / "latest_import_report.json",
        ground_truth_report_path=tmp_path / "missing_ground_truth.json",
        inference_report_path=tmp_path / "missing_inference.json",
    )
    payload = json.loads(Path(result["review_evidence_json"]).read_text(encoding="utf-8"))
    item = payload["items"][0]
    assert item["power_original"] == 767730565
    assert item["best_candidate"] == 167730565
    assert item["second_candidate"] == 159730565
    assert item["trace_status"] == "ambiguous"
    html = Path(result["review_evidence_pack"]).read_text(encoding="utf-8")
    assert "167730565" in html
    assert "Digit" in html


def test_review_evidence_contains_human_problem_and_history(tmp_path: Path):
    data = tmp_path / "data"
    output = tmp_path / "output"
    data.mkdir()
    (data / "latest_import_report.json").write_text(json.dumps({
        "status": "Review",
        "readiness": 50,
        "created_at": "2026-07-02T13:52:10Z",
        "review_item_count": 1,
        "power_recovery": {"recovered": 0, "ambiguous": 1, "traces": [{
            "server": None,
            "ranking_type": "ranking_guard_quarantine",
            "rank": 3,
            "source_file": "shot.png",
            "name": "Ambiguous Player",
            "power_original": 767730565,
            "power_selected": 767730565,
            "status": "ambiguous",
            "best_candidate": 167730565,
            "second_candidate": 159730565,
            "best_score": 0.7124,
            "second_score": 0.6939,
            "margin": 0.0185,
            "candidate_count": 2,
            "decision_reason": "quarantined_ambiguous_candidates",
            "candidates": [
                {"value": 167730565, "score": 0.7124, "reasons": ["ocr_error_model:leading_digit_to_1"]},
                {"value": 159730565, "score": 0.6939, "reasons": ["source_local_bucket_match"]},
            ],
        }]},
        "reviews": [{
            "server": 554,
            "ranking_type": "total_hero_power",
            "expected_ranking_type": "total_hero_power",
            "rank": 3,
            "title": "Ranking Guard quarantine",
            "reason": "ranking_guard_quarantine",
            "description": "power_sanity:power_recovery_candidates_ambiguous;ambiguous_candidates:best=0.712;margin=0.019",
            "screenshot": "shot.png",
        }],
    }), encoding="utf-8")

    result = generate_command_center(
        output_dir=output,
        import_report_path=data / "latest_import_report.json",
        ground_truth_report_path=tmp_path / "missing_ground_truth.json",
        inference_report_path=tmp_path / "missing_inference.json",
    )
    evidence = json.loads(Path(result["review_evidence_json"]).read_text(encoding="utf-8"))
    item = evidence["items"][0]
    assert item["problem_type"] == "power_ambiguous"
    assert "Ich konnte" in item["problem_statement"]
    assert item["choices"][0]["label"] == "Vorschlag 1"
    assert item["choices"][-1]["kind"] == "manual_input"
    html = Path(result["review_evidence_pack"]).read_text(encoding="utf-8")
    assert "Problem:" in html
    assert "Review choices" in html
    history = json.loads(Path(result["review_history_json"]).read_text(encoding="utf-8"))
    assert history["schema"] == "sentinel.review_history.v1"
    assert history["open_count"] == 1
    assert Path(result["review_history_store"]).exists()
