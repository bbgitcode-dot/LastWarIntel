from ground_truth_validator import _is_latin_residual_core_identity


def test_latin_residual_policy_accepts_expected_core_contained_in_observed_noise():
    ok, reason = _is_latin_residual_core_identity(
        accepted_match=True,
        name_category="latin_only",
        power_match=True,
        verified_alliance_display_exact=True,
        verified_name_display_exact=False,
        raw_name_normalized_match=False,
        name_normalized_similarity=0.60,
        expected_name_latin_core="Zed",
        actual_name_latin_core="XZed 00 5",
        expected_name_key="ZED",
        actual_name_key="XZEDOOS",
        skipped_player_targets=7,
        unresolved_player_evidence=0,
    )
    assert ok is True
    assert reason == "latin_residual_core_contained_in_observed"


def test_latin_residual_policy_accepts_high_similarity_clean_case_or_spacing():
    ok, reason = _is_latin_residual_core_identity(
        accepted_match=True,
        name_category="latin_only",
        power_match=True,
        verified_alliance_display_exact=True,
        verified_name_display_exact=False,
        raw_name_normalized_match=True,
        name_normalized_similarity=0.97,
        expected_name_latin_core="Tinyy ZEZE",
        actual_name_latin_core="TinyyZEZE",
        expected_name_key="TINYYZEZE",
        actual_name_key="TINYYZEZE",
        skipped_player_targets=0,
        unresolved_player_evidence=0,
    )
    assert ok is True
    assert reason in {"latin_residual_core_contained_in_observed", "latin_residual_high_similarity_clean"}


def test_latin_residual_policy_rejects_broad_missing_glyphs():
    drpeek, drpeek_reason = _is_latin_residual_core_identity(
        accepted_match=True,
        name_category="latin_only",
        power_match=True,
        verified_alliance_display_exact=True,
        verified_name_display_exact=False,
        raw_name_normalized_match=False,
        name_normalized_similarity=0.60,
        expected_name_latin_core="Drpeek",
        actual_name_latin_core="Ieek",
        expected_name_key="DRPEEK",
        actual_name_key="IEEK",
        skipped_player_targets=2,
        unresolved_player_evidence=0,
    )
    assert drpeek is False
    assert drpeek_reason == "latin_residual_not_stable"

    nerd, nerd_reason = _is_latin_residual_core_identity(
        accepted_match=True,
        name_category="latin_only",
        power_match=True,
        verified_alliance_display_exact=True,
        verified_name_display_exact=False,
        raw_name_normalized_match=False,
        name_normalized_similarity=0.75,
        expected_name_latin_core="N E R D",
        actual_name_latin_core="NER0",
        expected_name_key="NERD",
        actual_name_key="NERO",
        skipped_player_targets=0,
        unresolved_player_evidence=1,
    )
    assert nerd is False
    assert nerd_reason == "latin_residual_not_stable"


def test_latin_residual_policy_rejects_non_latin_and_unverified_alliance():
    non_latin, reason = _is_latin_residual_core_identity(
        accepted_match=True, name_category="mixed_latin_cjk", power_match=True,
        verified_alliance_display_exact=True, verified_name_display_exact=False,
        raw_name_normalized_match=True, name_normalized_similarity=1.0,
        expected_name_latin_core="YUNS", actual_name_latin_core="YUNS",
        expected_name_key="YUNS", actual_name_key="YUNS",
        skipped_player_targets=0, unresolved_player_evidence=0,
    )
    assert non_latin is False
    assert reason == "not_latin_only"

    no_alliance, reason = _is_latin_residual_core_identity(
        accepted_match=True, name_category="latin_only", power_match=True,
        verified_alliance_display_exact=False, verified_name_display_exact=False,
        raw_name_normalized_match=True, name_normalized_similarity=1.0,
        expected_name_latin_core="Zed", actual_name_latin_core="XZed",
        expected_name_key="ZED", actual_name_key="XZED",
        skipped_player_targets=0, unresolved_player_evidence=0,
    )
    assert no_alliance is False
    assert reason == "alliance_not_verified"
