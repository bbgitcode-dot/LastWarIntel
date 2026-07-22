import pandas as pd
from ground_truth_validator import _build_resolution_readiness_intelligence


def _frames():
    queue = pd.DataFrame([
        {
            "case_id":"S551-R20","server":551,"rank":20,"priority":"MAJOR",
            "review_action":"REVIEW_LOCAL_GLYPH","failure_class":"local_glyph_solvable",
            "failure_domain":"local_glyph","identity_composition_status":"COMPOSED",
            "required_evidence":"character crop; OCR candidates; vote consensus; provenance chain",
            "case_binding_status":"BOUND","gold_clearance_created":False,
        },
        {
            "case_id":"S551-R8","server":551,"rank":8,"priority":"CRITICAL",
            "review_action":"REVIEW_MISSING_IDENTITY","failure_class":"vote_warning_gate_review",
            "failure_domain":"vote_selection","identity_composition_status":"UNKNOWN_PROTECTED",
            "required_evidence":"complete screenshot; uncropped row; OCR observation set",
            "case_binding_status":"BOUND","gold_clearance_created":False,
        },
        {
            "case_id":"S551-R42","server":551,"rank":42,"priority":"CRITICAL",
            "review_action":"REVIEW_EVIDENCE_CONFLICT","failure_class":"observed_text_confirmed",
            "failure_domain":"evidence_against_expected","identity_composition_status":"COMPOSED",
            "required_evidence":"observed source characters; alignment operations; conflicting position evidence",
            "case_binding_status":"BOUND","gold_clearance_created":False,
        },
    ])
    bindings = pd.DataFrame([
        {"case_id":"S551-R20","binding_confidence":1.0},
        {"case_id":"S551-R8","binding_confidence":1.0},
        {"case_id":"S551-R42","binding_confidence":1.0},
    ])
    confidence = pd.DataFrame([
        {"case_id":"S551-R20","provenance_confidence":1.0,"observation_confidence":0.9,"semantic_identity_confidence":0.84},
        {"case_id":"S551-R8","provenance_confidence":1.0,"observation_confidence":0.9,"semantic_identity_confidence":0.0},
        {"case_id":"S551-R42","provenance_confidence":1.0,"observation_confidence":0.82,"semantic_identity_confidence":0.69},
    ])
    return queue, bindings, confidence


def test_resolution_readiness_scores_and_classifies_without_clearance():
    cases, breakdown, validation, summary = _build_resolution_readiness_intelligence(*_frames())
    assert len(cases) == 3
    assert (cases["root_cause_confidence"] > 0).all()
    assert (cases["recommendation_score"] > 0).all()
    assert cases["review_confidence"].nunique() > 1
    assert cases["resolution_readiness"].astype(str).str.strip().ne("").all()
    assert cases["resolution_strategy"].astype(str).str.strip().ne("").all()
    assert not cases["gold_clearance_created"].any()
    assert not cases["automatic_fix_executed"].any()
    assert not cases["ground_truth_used_as_evidence"].any()
    assert not cases["operational_truth_modified"].any()
    assert (validation["status"] == "PASS").all()
    assert int(summary.iloc[0]["cases"]) == 3
    assert not breakdown.empty


def test_unknown_waits_for_evidence_and_conflict_requires_manual_review():
    cases, *_ = _build_resolution_readiness_intelligence(*_frames())
    unknown = cases[cases["case_id"] == "S551-R8"].iloc[0]
    conflict = cases[cases["case_id"] == "S551-R42"].iloc[0]
    assert unknown["resolution_readiness"] == "WAITING_FOR_EVIDENCE"
    assert unknown["resolution_strategy"] == "COLLECT_IDENTITY_EVIDENCE"
    assert conflict["resolution_readiness"] == "READY_FOR_MANUAL_REVIEW"
    assert conflict["resolution_strategy"] == "MANUAL_EVIDENCE_ADJUDICATION"
