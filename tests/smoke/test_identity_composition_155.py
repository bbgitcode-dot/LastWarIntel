import pandas as pd

from ground_truth_validator import _build_identity_composition_engine


def test_identity_composition_preserves_unknown_and_creates_review_queue():
    cases = pd.DataFrame([{
        "server": 551, "rank": 4, "observed_identity_text": "UNKNOWN",
        "unknown_protected": True, "components": 1,
        "failure_class": "crop_geometry_problem", "failure_domain": "crop",
        "fix_lane": "geometry", "root_cause": "missing identity crop",
        "recommendation": "review crop",
    }])
    chars = pd.DataFrame([{
        "server": 551, "rank": 4, "character_id": "char:0",
        "source_chain_status": "ROW_OCR_SOURCE_BOUND", "source_screenshot": "s1.png",
        "source_observation_id": "obs-1",
    }])
    tokens = pd.DataFrame([{
        "server": 551, "rank": 4, "token_id": "token:0",
        "character_ids": ["char:0"],
    }])
    components = pd.DataFrame([{
        "server": 551, "rank": 4, "component_id": "component:0",
        "component_type": "UNKNOWN_SENTINEL", "component_text": "UNKNOWN",
        "token_ids": ["token:0"], "classification_confidence": 1.0,
    }])
    compositions, slots, review, roots, priorities = _build_identity_composition_engine(cases, chars, tokens, components)
    assert compositions.iloc[0]["identity_composition_status"] == "UNKNOWN_PROTECTED"
    assert compositions.iloc[0]["gold_clearance_created"] == False
    assert slots.iloc[0]["identity_slot"] == "UNKNOWN_SEGMENT"
    assert slots.iloc[0]["ground_truth_used_as_evidence"] == False
    assert review.iloc[0]["priority"] == "CRITICAL"
    assert review.iloc[0]["recommended_action"] == "REVIEW_CROP_GEOMETRY"
    assert not roots.empty
    assert not priorities.empty


def test_identity_composition_builds_player_name_and_title_slots():
    cases = pd.DataFrame([{
        "server": 551, "rank": 7, "observed_identity_text": "VIP Drpeek",
        "unknown_protected": False, "components": 2,
        "failure_class": "vote_warning_gate_review", "failure_domain": "identity",
        "fix_lane": "review", "root_cause": "vote conflict", "recommendation": "review votes",
    }])
    chars = pd.DataFrame([
        {"server":551,"rank":7,"character_id":"char:0","source_chain_status":"ROW_OCR_SOURCE_BOUND","source_screenshot":"s.png","source_observation_id":"o"},
        {"server":551,"rank":7,"character_id":"char:1","source_chain_status":"ROW_OCR_SOURCE_BOUND","source_screenshot":"s.png","source_observation_id":"o"},
    ])
    tokens = pd.DataFrame([
        {"server":551,"rank":7,"token_id":"token:0","character_ids":["char:0"]},
        {"server":551,"rank":7,"token_id":"token:1","character_ids":["char:1"]},
    ])
    components = pd.DataFrame([
        {"server":551,"rank":7,"component_id":"component:0","component_type":"TITLE_OR_PREFIX","component_text":"VIP","token_ids":["token:0"],"classification_confidence":0.7},
        {"server":551,"rank":7,"component_id":"component:1","component_type":"NAME_TOKEN","component_text":"Drpeek","token_ids":["token:1"],"classification_confidence":0.8},
    ])
    compositions, slots, review, _, _ = _build_identity_composition_engine(cases, chars, tokens, components)
    by_slot = {row.identity_slot: row.slot_value for row in slots.itertuples()}
    assert by_slot["TITLE_OR_PREFIX"] == "VIP"
    assert by_slot["PLAYER_NAME"] == "Drpeek"
    assert compositions.iloc[0]["identity_composition_status"] == "OBSERVED_IDENTITY_COMPOSED"
    assert 0 < compositions.iloc[0]["identity_confidence"] <= 1
    assert review.iloc[0]["recommended_action"] == "REVIEW_EVIDENCE_CONFLICT"
