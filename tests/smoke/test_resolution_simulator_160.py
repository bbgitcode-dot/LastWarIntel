import pandas as pd
from ground_truth_validator import _build_resolution_simulator


def _cases():
    return pd.DataFrame([
        {"case_id":"S551-R39","server":551,"rank":39,"failure_class":"crop_geometry_problem","review_action":"REVIEW_CROP_GEOMETRY","resolution_readiness":"READY_FOR_TARGETED_REOCR","resolution_strategy":"RECROP_AND_TARGETED_REOCR","required_evidence_coverage":1.0,"review_confidence":0.91,"recommendation_score":0.92,"priority":"MAJOR"},
        {"case_id":"S551-R8","server":551,"rank":8,"failure_class":"vote_warning_gate_review","review_action":"REVIEW_MISSING_IDENTITY","resolution_readiness":"WAITING_FOR_EVIDENCE","resolution_strategy":"COLLECT_IDENTITY_EVIDENCE","required_evidence_coverage":0.4,"review_confidence":0.73,"recommendation_score":0.75,"priority":"CRITICAL"},
        {"case_id":"S551-R2","server":551,"rank":2,"failure_class":"policy_nonlocal_script_display","review_action":"REVIEW_SCRIPT_POLICY","resolution_readiness":"POLICY_DECISION_REQUIRED","resolution_strategy":"MANUAL_SCRIPT_POLICY_REVIEW","required_evidence_coverage":0.75,"review_confidence":0.82,"recommendation_score":0.80,"priority":"CRITICAL"},
    ])


def test_simulator_covers_cases_with_multiple_ranked_options():
    cases, options, validation, summary = _build_resolution_simulator(_cases())
    assert len(cases) == 3
    assert (options.groupby("case_id").size() >= 2).all()
    assert options[options["recommended_option"]].groupby("case_id").size().eq(1).all()
    assert validation["status"].eq("PASS").all()
    assert int(summary.iloc[0]["recommended_options"]) == 3


def test_simulator_is_read_only_and_never_clears_gold():
    cases, options, validation, _ = _build_resolution_simulator(_cases())
    assert options["simulation_only"].all()
    assert not options["automatic_fix_executed"].any()
    assert not options["gold_clearance_created"].any()
    assert not options["ground_truth_used_as_evidence"].any()
    assert not options["operational_truth_modified"].any()
    assert not cases["automatic_fix_executed"].any()
    assert validation.loc[validation["guard"] == "simulation_is_read_only", "status"].iloc[0] == "PASS"


def test_simulator_prefers_expected_safe_strategy_for_known_lanes():
    cases, _, _, _ = _build_resolution_simulator(_cases())
    chosen = dict(zip(cases["case_id"], cases["recommended_simulated_strategy"]))
    assert chosen["S551-R39"] == "RECROP_AND_TARGETED_REOCR"
    assert chosen["S551-R8"] == "COLLECT_IDENTITY_EVIDENCE"
    assert chosen["S551-R2"] == "MANUAL_SCRIPT_POLICY_REVIEW"
