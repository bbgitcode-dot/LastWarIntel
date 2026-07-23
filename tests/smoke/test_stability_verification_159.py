import pandas as pd

from ground_truth_validator import _build_stability_verification_history


def _cases(failure_class="crop_geometry_problem", evidence="a" , readiness="READY_FOR_TARGETED_REOCR"):
    return pd.DataFrame([{
        "case_id":"S551-R39", "server":551, "rank":39,
        "evidence_fingerprint": evidence * 64,
        "classification_fingerprint": ("b" if failure_class == "crop_geometry_problem" else "c") * 64,
        "decision_hash": ("d" if readiness == "READY_FOR_TARGETED_REOCR" else "e") * 64,
        "failure_class": failure_class, "failure_domain":"crop_anchor_or_field_bleed",
        "review_action":"REVIEW_CROP_GEOMETRY", "resolution_readiness":readiness,
        "resolution_strategy":"RECROP_AND_TARGETED_REOCR", "root_cause_confidence":0.95,
        "recommendation_score":0.92, "review_confidence":0.89, "required_evidence_coverage":0.8,
    }])


def test_first_run_records_history_without_drift(tmp_path):
    history, timeline, drift, dashboard, validation, summary = _build_stability_verification_history(_cases(), tmp_path)
    assert len(history) == 1
    assert drift.iloc[0]["drift_attribution"] == "NO_PREVIOUS_BASELINE"
    assert summary.iloc[0]["runs"] == 1
    assert validation.set_index("guard").loc["no_unexplained_cross_run_drift", "status"] == "PASS"
    assert (tmp_path / "decision_history_state.json").exists()


def test_identical_rerun_is_stable_and_idempotent(tmp_path):
    _build_stability_verification_history(_cases(), tmp_path)
    history, _, drift, _, validation, summary = _build_stability_verification_history(_cases(), tmp_path)
    assert len(history) == 1
    assert drift.iloc[0]["drift_attribution"] == "STABLE"
    assert summary.iloc[0]["stable_cases"] == 1
    assert validation.set_index("guard").loc["no_unexplained_cross_run_drift", "status"] == "PASS"


def test_same_evidence_different_classification_is_critical(tmp_path):
    _build_stability_verification_history(_cases(), tmp_path)
    _, _, drift, _, validation, summary = _build_stability_verification_history(
        _cases(failure_class="observed_text_confirmed"), tmp_path
    )
    row = drift.iloc[0]
    assert row["drift_attribution"] == "UNEXPLAINED_CLASSIFICATION_DRIFT"
    assert row["severity"] == "CRITICAL"
    assert summary.iloc[0]["unexplained_drifts"] == 1
    assert validation.set_index("guard").loc["no_unexplained_cross_run_drift", "status"] == "FAIL"


def test_changed_evidence_explains_classification_change(tmp_path):
    _build_stability_verification_history(_cases(), tmp_path)
    _, _, drift, _, validation, _ = _build_stability_verification_history(
        _cases(failure_class="observed_text_confirmed", evidence="f"), tmp_path
    )
    assert drift.iloc[0]["drift_attribution"] == "EVIDENCE_CHANGED"
    assert validation.set_index("guard").loc["no_unexplained_cross_run_drift", "status"] == "PASS"
