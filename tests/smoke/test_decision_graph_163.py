from pathlib import Path
import pandas as pd
import ground_truth_validator as gtv


def _cases():
    return pd.DataFrame([{
        "case_id":"S551-R11","server":"551","rank":11,
        "evidence_fingerprint":"a"*64,"classification_fingerprint":"b"*64,"decision_hash":"c"*64,
        "failure_class":"vote_warning_gate_review","review_action":"TARGETED_REOCR",
        "resolution_readiness":"READY_FOR_TARGETED_REOCR","resolution_strategy":"REPLAY_VOTE_SELECTION_WITH_TARGETED_REOCR",
        "review_confidence":0.8,"required_evidence_coverage":0.75,
    }])


def test_case_uuid_is_stable_and_unique():
    first = gtv._case_uuid("S551-R11")
    second = gtv._case_uuid("S551-R11")
    other = gtv._case_uuid("S551-R12")
    assert first == second
    assert first != other
    assert len(first) == 36


def test_decision_graph_builds_complete_chain():
    stability = _cases()
    simulation = pd.DataFrame([{
        "case_id":"S551-R11","primary_strategy":"REPLAY_VOTE_SELECTION_WITH_TARGETED_REOCR",
        "prerequisite_action":"","recommended_option":"REPLAY_VOTE_SELECTION_WITH_TARGETED_REOCR",
        "strategy_relationship":"DIRECT",
    }])
    identity = pd.DataFrame([{"case_id":"S551-R11","identity_status":"UNRESOLVED"}])
    provenance = pd.DataFrame([{"case_id":"S551-R11","first_failed_stage":"vote_selection"}])
    review = pd.DataFrame([{"case_id":"S551-R11","review_action":"TARGETED_REOCR"}])
    history = pd.DataFrame([{"case_id":"S551-R11","run_id":"run-1"}])
    cases, nodes, edges, validation, summary = gtv._build_decision_graph(
        stability, simulation, identity, provenance, review, history
    )
    assert len(cases) == 1
    assert len(nodes) == 7
    assert len(edges) == 6
    assert validation["status"].eq("PASS").all()
    assert summary.iloc[0]["cross_layer_consistency"] == "PASS"
    assert cases.iloc[0]["operational_truth_modified"] == False
    assert cases.iloc[0]["gold_clearance_created"] == False


def test_decision_graph_preserves_prerequisite_chain():
    stability = _cases()
    simulation = pd.DataFrame([{
        "case_id":"S551-R11","primary_strategy":"MANUAL_SCRIPT_POLICY_REVIEW",
        "prerequisite_action":"COLLECT_SCRIPT_CONTEXT","recommended_option":"COLLECT_SCRIPT_CONTEXT",
        "strategy_relationship":"PREREQUISITE",
    }])
    cases, *_ = gtv._build_decision_graph(
        stability, simulation, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    )
    row = cases.iloc[0]
    assert row["primary_strategy"] == "MANUAL_SCRIPT_POLICY_REVIEW"
    assert row["prerequisite_action"] == "COLLECT_SCRIPT_CONTEXT"
    assert row["strategy_relationship"] == "PREREQUISITE"
