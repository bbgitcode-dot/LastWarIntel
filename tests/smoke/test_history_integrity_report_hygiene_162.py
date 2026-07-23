from pathlib import Path
import json
import pandas as pd
import ground_truth_validator as gtv


def _cases():
    return pd.DataFrame([{
        "case_id":"S551-R19","server":551,"rank":19,
        "evidence_fingerprint":"a"*64,"classification_fingerprint":"b"*64,"decision_hash":"c"*64,
        "failure_class":"mixed_local_and_nonlocal_blocker","failure_domain":"script_policy",
        "review_action":"REVIEW_MIXED_SCRIPT","resolution_readiness":"POLICY_DECISION_REQUIRED",
        "resolution_strategy":"MANUAL_SCRIPT_POLICY_REVIEW","root_cause_confidence":0.8,
        "recommendation_score":0.8,"review_confidence":0.7,"required_evidence_coverage":0.5,
        "priority":"MAJOR",
    }])


def test_new_run_id_records_stable_observation(tmp_path):
    gtv._build_stability_verification_history(_cases(), tmp_path, gtv.RELEASE_VERSION, "run-a")
    history, _, drift, _, _, summary = gtv._build_stability_verification_history(_cases(), tmp_path, gtv.RELEASE_VERSION, "run-b")
    assert len(history) == 2
    assert summary.iloc[0]["runs"] == 2
    assert drift.iloc[0]["drift_attribution"] == "STABLE"
    assert history["decision_state_hash"].nunique() == 1


def test_same_run_id_remains_idempotent(tmp_path):
    gtv._build_stability_verification_history(_cases(), tmp_path, gtv.RELEASE_VERSION, "run-a")
    history, *_ = gtv._build_stability_verification_history(_cases(), tmp_path, gtv.RELEASE_VERSION, "run-a")
    assert len(history) == 1


def test_prerequisite_chain_is_compatible_not_conflict():
    cases, _, _, summary = gtv._build_resolution_simulator(_cases())
    row = cases.iloc[0]
    assert row["strategy_relationship"] in {"ALIGNED", "PREREQUISITE"}
    assert bool(row["strategy_alignment"])
    assert int(summary.iloc[0]["true_strategy_conflicts"]) == 0


def test_wrong_scope_snapshot_reports_are_removed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wrong = tmp_path / "reports" / "snapshots" / "wrong-scope-deadbeef"
    good = tmp_path / "reports" / "snapshots" / "active-1"
    wrong.mkdir(parents=True)
    good.mkdir(parents=True)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "managed_snapshots.json").write_text(json.dumps({"active_snapshot_id":"active-1"}), encoding="utf-8")
    result = gtv._clean_snapshot_report_hygiene(tmp_path / "reports")
    assert result["removed_snapshot_report_dirs"] == 1
    assert not wrong.exists()
    assert good.exists()
