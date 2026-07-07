from ground_truth_validator import _should_run_latin_name_block_reconstruction


def test_block_reconstruction_skips_when_glyphs_already_resolved():
    run, reason = _should_run_latin_name_block_reconstruction(
        accepted_match=True,
        name_category="latin_only",
        raw_name_display_exact=False,
        expected_name="Joncollins21",
        actual_name="Joncollinszl",
        row_slot=0,
        raw_power_match=True,
        raw_alliance_match=True,
        raw_player_targets=2,
        local_player_targets=2,
        skipped_player_targets=0,
        verified_player_expected=2,
        unresolved_player_evidence=0,
    )
    assert run is False
    assert reason == "glyphs_already_resolved"


def test_block_reconstruction_runs_for_residual_latin_gap():
    run, reason = _should_run_latin_name_block_reconstruction(
        accepted_match=True,
        name_category="latin_only",
        raw_name_display_exact=False,
        expected_name="Mizzenmast",
        actual_name="Mzzenmast",
        row_slot=2,
        raw_power_match=True,
        raw_alliance_match=True,
        raw_player_targets=1,
        local_player_targets=1,
        skipped_player_targets=0,
        verified_player_expected=0,
        unresolved_player_evidence=1,
    )
    assert run is True
    assert reason == "eligible_player_name_block_residual"


def test_block_reconstruction_rejects_unknown_and_nonlocal():
    run_unknown, reason_unknown = _should_run_latin_name_block_reconstruction(
        accepted_match=True,
        name_category="latin_only",
        raw_name_display_exact=False,
        expected_name="GD VIP",
        actual_name="UNKNOWN",
        row_slot=0,
        raw_power_match=True,
        raw_alliance_match=True,
        raw_player_targets=2,
        local_player_targets=2,
        skipped_player_targets=0,
        verified_player_expected=0,
        unresolved_player_evidence=2,
    )
    assert run_unknown is False
    assert reason_unknown == "observed_unknown"

    run_nonlocal, reason_nonlocal = _should_run_latin_name_block_reconstruction(
        accepted_match=True,
        name_category="latin_only",
        raw_name_display_exact=False,
        expected_name="Tinyy ZEZE",
        actual_name="0觋咀#_ Tinyy ZEZE",
        row_slot=5,
        raw_power_match=True,
        raw_alliance_match=True,
        raw_player_targets=6,
        local_player_targets=1,
        skipped_player_targets=5,
        verified_player_expected=0,
        unresolved_player_evidence=1,
    )
    assert run_nonlocal is False
    assert reason_nonlocal == "nonlocal_player_targets_present"
