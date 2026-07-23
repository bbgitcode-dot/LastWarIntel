from pathlib import Path
import json
import pandas as pd

import ground_truth_validator as gtv


def _frame(**cols):
    return pd.DataFrame([cols])


def test_default_report_root_is_not_benchmarks():
    assert gtv.DEFAULT_OUTPUT_DIR == Path("reports")


def test_legacy_state_migrates_and_reports_are_removed(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bench = tmp_path / "benchmarks"
    bench.mkdir()
    (bench / "decision_history_state.json").write_text('{"history": []}', encoding="utf-8")
    (bench / "resolution_simulator_report.json").write_text('{}', encoding="utf-8")
    (bench / "runtime.log").write_text('keep', encoding="utf-8")

    result = gtv._migrate_and_clean_legacy_benchmark_reports(tmp_path / "reports", tmp_path / "output" / "lastwar_export.xlsx")

    assert result["migrated_state_files"] == 1
    assert (tmp_path / "reports" / "state" / "decision_history_state.json").exists()
    assert not (bench / "decision_history_state.json").exists()
    assert not (bench / "resolution_simulator_report.json").exists()
    assert (bench / "runtime.log").exists()


def test_report_architecture_publishes_compact_artifacts(tmp_path: Path):
    root = tmp_path / "reports"
    root.mkdir()
    (root / "old_report.json").write_text('{}', encoding="utf-8")
    (root / "GOLD_CORE_CASEBOOK.md").write_text('# cases', encoding="utf-8")
    one = _frame(case_id="S551-R19", cases=1, options=3, operational_truth_modified=False)
    gtv._publish_report_architecture(
        root,
        json_payload={"summary": {"recall": 1.0}}, summary_rows=[{"recall": 1.0}],
        regression_dashboard_rows=one, resolution_readiness_summary=one,
        resolution_readiness_cases=one, resolution_simulation_summary=one,
        resolution_simulation_cases=one, resolution_simulation_options=one,
        resolution_simulation_validation=one, manual_review_queue=one,
        gold_core_case_explorer=one, gold_core_prioritized_actions=one,
        classification_stability_cases=one, decision_history_rows=one,
        stability_timeline_rows=one, drift_analysis_rows=one,
        evidence_coverage_rows=one, score_decomposition_rows=one,
        review_case_bindings=one, review_confidence_calibration=one,
        identity_compositions=one, identity_slots=one, identity_graph_cases=one,
        evidence_provenance_cases=one, position_bridge_cases=one,
        runtime_payload={"summary": {}}, runtime_phase_df=one,
    )
    assert (root / "executive" / "SENTINEL_EXECUTIVE_REPORT.xlsx").exists()
    assert (root / "operations" / "SENTINEL_RESOLUTION_WORKBENCH.xlsx").exists()
    assert (root / "operations" / "GOLD_CORE_CASEBOOK.md").exists()
    assert (root / "intelligence" / "SENTINEL_INTELLIGENCE_REPORT.json").exists()
    assert (root / "diagnostics" / "SENTINEL_RUNTIME_DIAGNOSTICS.xlsx").exists()
    assert not (root / "old_report.json").exists()


def test_rank_19_can_express_prerequisite_without_replacing_primary_strategy():
    cases = pd.DataFrame([{
        "case_id": "S551-R19", "server": 551, "rank": 19,
        "failure_class": "mixed_local_and_nonlocal_blocker",
        "review_action": "MANUAL_SCRIPT_POLICY_REVIEW",
        "resolution_readiness": "POLICY_DECISION_REQUIRED",
        "resolution_strategy": "MANUAL_SCRIPT_POLICY_REVIEW",
        "required_evidence_coverage": 0.5, "review_confidence": 0.5,
        "recommendation_score": 0.5, "priority": "MAJOR",
    }])
    simulated, _, _, _ = gtv._build_resolution_simulator(cases)
    row = simulated.iloc[0]
    assert row["primary_strategy"] == "MANUAL_SCRIPT_POLICY_REVIEW"
    if row["recommended_simulated_strategy"] != row["primary_strategy"]:
        assert row["strategy_relationship"] == "PREREQUISITE"
        assert row["prerequisite_action"] == row["recommended_simulated_strategy"]
