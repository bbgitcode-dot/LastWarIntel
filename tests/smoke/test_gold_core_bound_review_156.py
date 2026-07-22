import pandas as pd
from ground_truth_validator import _build_gold_core_bound_review_orchestration


def _base():
    compositions = pd.DataFrame([
        {"server":551,"rank":8,"observed_identity_text":"UNKNOWN","identity_composition_status":"UNKNOWN_PROTECTED","identity_confidence":0.0,"slot_count":1,"component_count":1},
        {"server":551,"rank":39,"observed_identity_text":"Beast 召合","identity_composition_status":"OBSERVED_IDENTITY_COMPOSED","identity_confidence":0.82,"slot_count":3,"component_count":3},
    ])
    slots = pd.DataFrame([
        {"server":551,"rank":8,"identity_slot":"UNKNOWN_SEGMENT","token_confidence":0.0,"component_provenance_complete":True},
        {"server":551,"rank":39,"identity_slot":"PLAYER_NAME","token_confidence":0.9,"component_provenance_complete":True},
        {"server":551,"rank":39,"identity_slot":"SCRIPT_BLOCK","token_confidence":0.7,"component_provenance_complete":True},
    ])
    blockers = pd.DataFrame([
        {"server":551,"rank":8,"gold_core_blocker":True,"gold_core_failure_class":"vote_warning_gate_review","gold_core_failure_domain":"vote_selection_policy","gold_core_fix_lane":"safe_warning_downgrade_candidate","gold_core_next_safe_action":"Keep blocked."},
        {"server":551,"rank":39,"gold_core_blocker":True,"gold_core_failure_class":"crop_geometry_problem","gold_core_failure_domain":"crop_anchor_or_field_bleed","gold_core_fix_lane":"crop_geometry","gold_core_next_safe_action":"Fix crop."},
    ])
    resolution = pd.DataFrame([
        {"server":551,"rank":8,"gold_core_resolution_action":"P1_WARNING_DOWNGRADE_BLOCKED_BY_CORE","gold_core_resolution_lane":"vote_warning_policy","gold_core_resolution_recommendation":"Keep blocked until identity proof.","gold_core_resolution_root_cause":"vote_selection_policy"},
        {"server":551,"rank":39,"gold_core_resolution_action":"P1_CROP_GEOMETRY_FIRST","gold_core_resolution_lane":"crop_geometry","gold_core_resolution_recommendation":"Fix crop geometry first.","gold_core_resolution_root_cause":"crop_anchor_or_field_bleed"},
    ])
    return compositions, slots, pd.DataFrame(), blockers, resolution


def test_156_binds_authoritative_metadata_and_concrete_actions():
    result = _build_gold_core_bound_review_orchestration(*_base())
    comp, queue, roots, priorities, bindings, confidence, validation, summary = result
    assert len(queue) == 2
    assert set(queue["failure_class"]) == {"vote_warning_gate_review", "crop_geometry_problem"}
    assert "matched" not in set(queue["failure_class"].str.lower())
    q8 = queue[queue["rank"] == 8].iloc[0]
    q39 = queue[queue["rank"] == 39].iloc[0]
    assert q8["priority"] == "CRITICAL"  # UNKNOWN escalation
    assert q8["review_action"] == "REVIEW_MISSING_IDENTITY"
    assert q39["priority"] == "MAJOR"
    assert q39["review_action"] == "REVIEW_CROP_GEOMETRY"
    assert bindings["join_status"].eq("BOUND").all()
    assert validation["status"].eq("PASS").all()
    assert summary.iloc[0]["queue_coverage_percent"] == 100.0
    assert not queue["gold_clearance_created"].any()


def test_156_binding_failure_is_visible_and_never_silent():
    compositions, slots, legacy, blockers, resolution = _base()
    compositions.loc[1, "rank"] = 40
    result = _build_gold_core_bound_review_orchestration(compositions, slots, legacy, blockers, resolution)
    queue, bindings, validation = result[1], result[4], result[6]
    failed = queue[queue["rank"] == 40].iloc[0]
    assert failed["failure_class"] == "CASE_BINDING_ERROR"
    assert failed["review_action"] == "REVIEW_CASE_BINDING"
    assert bindings[bindings["rank"] == 40].iloc[0]["join_status"] == "MISSING"
    assert (validation["status"] == "FAIL").any()
