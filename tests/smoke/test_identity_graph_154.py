import pandas as pd
from ground_truth_validator import _tokenize_identity_observation, _classify_identity_components, _build_player_identity_graph


def test_identity_graph_tokenizes_script_and_title_blocks():
    chars, tokens = _tokenize_identity_observation("GD VIP 지디", [])
    texts = [t["token_text"] for t in tokens]
    assert "GD" in texts
    assert "VIP" in texts
    assert "지디" in texts
    comps = _classify_identity_components("GD VIP 지디", "", tokens)
    kinds = [c["component_type"] for c in comps]
    assert "TITLE_OR_PREFIX" in kinds
    assert "SCRIPT_NAME_BLOCK" in kinds
    assert all(c["gold_authoritative"] is False for c in comps)


def test_unknown_is_one_protected_identity_state():
    _, tokens = _tokenize_identity_observation("UNKNOWN", [])
    comps = _classify_identity_components("UNKNOWN", "", tokens)
    assert comps
    assert all(c["component_type"] == "UNKNOWN_SENTINEL" for c in comps)


def test_graph_is_read_only_and_creates_no_clearance():
    detail = pd.DataFrame([{
        "server": 551, "rank": 8, "ocr_name": "GD VIP 지디", "ocr_alliance_tag": "",
        "display_reconstructed_name": "GD VIP 지디", "display_reconstructed_alliance_tag": "",
        "display_character_provenance": "[]", "gold_core_blocker": True,
        "gold_core_failure_class": "vote_warning_gate_review",
    }])
    cases, chars, tokens, comps, edges = _build_player_identity_graph(detail)
    assert len(cases) == 1
    assert cases.iloc[0]["ground_truth_used_as_evidence"] == False
    assert cases.iloc[0]["gold_clearance_created"] == False
    assert cases.iloc[0]["operational_truth_modified"] == False
    assert not chars.empty and not tokens.empty and not comps.empty and not edges.empty
