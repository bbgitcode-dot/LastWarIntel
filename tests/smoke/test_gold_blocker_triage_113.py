import pandas as pd

from ground_truth_validator import _build_gold_blocker_triage


def test_gold_blocker_triage_classifies_local_player_glyph_unresolved():
    blockers = pd.DataFrame([
        {
            "rank": 15,
            "gold_fidelity_blocker": True,
            "verified_name_display_exact_match": False,
            "verified_alliance_display_exact_match": True,
            "rank_match": True,
            "power_match": True,
            "power_exact_match": True,
            "alignment_context_gap": False,
            "character_reocr_unresolved": 1,
            "character_reocr_targets": 1,
            "character_reocr_skipped_nonlocal": 0,
            "name_category": "latin_only",
            "verified_identity_resolution": False,
            "name_similarity": 0.94,
            "power_similarity": 1.0,
        }
    ])

    triage, summary = _build_gold_blocker_triage(blockers)

    assert triage.loc[0, "gold_blocker_class"] == "local_player_glyph_unresolved"
    assert triage.loc[0, "gold_blocker_domain"] == "player_name"
    assert bool(triage.loc[0, "gold_blocker_is_local_glyph_candidate"])
    assert summary.loc[0, "rows"] == 1


def test_gold_blocker_triage_classifies_multilingual_nonlocal():
    blockers = pd.DataFrame([
        {
            "rank": 2,
            "gold_fidelity_blocker": True,
            "verified_name_display_exact_match": False,
            "verified_alliance_display_exact_match": True,
            "rank_match": True,
            "power_match": True,
            "power_exact_match": True,
            "alignment_context_gap": False,
            "character_reocr_unresolved": 0,
            "character_reocr_targets": 0,
            "character_reocr_skipped_nonlocal": 5,
            "name_category": "mixed_latin_cjk",
            "verified_identity_resolution": False,
            "name_similarity": 0.6,
            "power_similarity": 1.0,
        }
    ])

    triage, _ = _build_gold_blocker_triage(blockers)

    assert triage.loc[0, "gold_blocker_class"] == "nonlocal_or_multilingual_player_display_drift"
    assert triage.loc[0, "gold_blocker_priority"] == "P1"
    assert bool(triage.loc[0, "gold_blocker_is_multilingual_or_nonlocal"])
