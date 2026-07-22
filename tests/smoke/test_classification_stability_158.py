import json
import pandas as pd
from ground_truth_validator import _build_classification_stability_and_coverage


def _cases():
    return pd.DataFrame([
        {"case_id":"S551-R8","server":551,"rank":8,"review_action":"REVIEW_MISSING_IDENTITY","failure_class":"vote_warning_gate_review","failure_domain":"vote_selection","observed_identity_text":"UNKNOWN","identity_composition_status":"UNKNOWN_PROTECTED","case_binding_status":"BOUND","binding_confidence":1.0,"provenance_confidence":1.0,"observation_confidence":0.9,"semantic_identity_confidence":0.0,"root_cause_confidence":0.80,"recommendation_score":0.75,"review_confidence":0.73,"classification_source":"gold_core_blocker_report","gold_clearance_created":False,"automatic_fix_executed":False,"resolution_readiness":"WAITING_FOR_EVIDENCE","resolution_strategy":"COLLECT_IDENTITY_EVIDENCE"},
        {"case_id":"S551-R39","server":551,"rank":39,"review_action":"REVIEW_CROP_GEOMETRY","failure_class":"crop_geometry_problem","failure_domain":"crop_anchor_or_field_bleed","observed_identity_text":"Beast","identity_composition_status":"COMPOSED","case_binding_status":"BOUND","binding_confidence":1.0,"provenance_confidence":1.0,"observation_confidence":0.9,"semantic_identity_confidence":0.8,"root_cause_confidence":0.95,"recommendation_score":0.92,"review_confidence":0.90,"classification_source":"gold_core_blocker_report","source_screenshots":"screen.png","source_observations":"obs","gold_clearance_created":False,"automatic_fix_executed":False,"resolution_readiness":"READY_FOR_TARGETED_REOCR","resolution_strategy":"RECROP_AND_TARGETED_REOCR"},
    ])


def test_action_specific_coverage_and_score_explanations(tmp_path):
    cases, coverage, factors, validation, summary = _build_classification_stability_and_coverage(_cases(), tmp_path)
    assert cases["required_evidence_coverage"].nunique() > 1
    assert cases["evidence_fingerprint"].str.len().eq(64).all()
    assert cases["root_cause_confidence_label"].ne("").all()
    assert len(factors) == len(cases) * 14
    assert (validation["status"] == "PASS").all()
    assert (tmp_path / "classification_stability_state.json").exists()


def test_unexplained_classification_change_is_critical(tmp_path):
    first, *_ = _build_classification_stability_and_coverage(_cases(), tmp_path)
    changed = _cases()
    changed.loc[changed.case_id == "S551-R39", "failure_class"] = "observed_text_confirmed"
    second, _, _, validation, _ = _build_classification_stability_and_coverage(changed, tmp_path)
    row = second[second.case_id == "S551-R39"].iloc[0]
    assert bool(row["classification_changed"])
    assert not bool(row["evidence_changed"])
    assert row["classification_change_reason"] == "UNEXPLAINED_CLASSIFICATION_CHANGE"
    assert row["stability_severity"] == "CRITICAL"
    guard = validation[validation.guard == "no_unexplained_classification_change"].iloc[0]
    assert guard["status"] == "FAIL"


def test_evidence_change_explains_classification_change(tmp_path):
    _build_classification_stability_and_coverage(_cases(), tmp_path)
    changed = _cases()
    changed.loc[changed.case_id == "S551-R39", "failure_class"] = "observed_text_confirmed"
    changed.loc[changed.case_id == "S551-R39", "source_observations"] = "new observation"
    second, *_ = _build_classification_stability_and_coverage(changed, tmp_path)
    row = second[second.case_id == "S551-R39"].iloc[0]
    assert bool(row["evidence_changed"])
    assert row["classification_change_reason"] == "EVIDENCE_CHANGED"
