import pandas as pd

from ground_truth_validator import _build_character_acquisition_report, _character_observation_confidence


def test_character_acquisition_builds_consensus_and_heatmap_without_operational_write():
    detail = pd.DataFrame([{"server": 551, "rank": 1, "expected_name": "Joncollins21", "ocr_name": "Joncollinszl"}])
    debug = pd.DataFrame([
        {
            "server": 551,
            "rank": 1,
            "target_field": "player_name",
            "target_position": 10,
            "target_expected": "2",
            "target_observed": "z",
            "target_status": "verified_expected",
            "selected": "2",
            "confidence": 1.0,
            "nonempty_vote_chars": "2;2;2",
            "debug_read": "verified_expected",
            "crop_anchor_status": "anchor_seen",
            "crop_width": 20,
            "crop_height": 50,
        },
        {
            "server": 551,
            "rank": 1,
            "target_field": "player_name",
            "target_position": 11,
            "target_expected": "1",
            "target_observed": "l",
            "target_status": "verified_expected",
            "selected": "1",
            "confidence": 0.9,
            "nonempty_vote_chars": "1;1",
            "debug_read": "verified_expected",
            "crop_anchor_status": "anchor_seen",
            "crop_width": 22,
            "crop_height": 50,
        },
    ])

    summary, rows, heatmap, detail_out = _build_character_acquisition_report(detail, debug)

    assert not summary.empty
    assert set(rows["consensus_status"]) == {"consensus_verified_expected"}
    assert int(rows["observation_count"].sum()) == 2
    assert rows["character_acquisition_operational_truth_modified"].eq(False).all()
    assert int(detail_out.loc[0, "character_acquisition_positions"]) == 2
    assert int(detail_out.loc[0, "character_acquisition_verified_positions"]) == 2
    assert bool(detail_out.loc[0, "character_acquisition_operational_truth_modified"]) is False
    assert not heatmap.empty


def test_character_acquisition_confidence_penalizes_field_mismatch():
    clean = pd.Series({
        "target_status": "verified_expected",
        "selected": "G",
        "confidence": 1.0,
        "nonempty_vote_chars": "G;G;G",
        "debug_read": "verified_expected",
        "crop_anchor_status": "anchor_seen",
        "crop_width": 20,
        "crop_height": 50,
    })
    noisy = clean.copy()
    noisy["debug_read"] = "crop_field_mismatch"
    noisy["crop_anchor_status"] = "field_mismatch"

    assert _character_observation_confidence(clean) > _character_observation_confidence(noisy)
