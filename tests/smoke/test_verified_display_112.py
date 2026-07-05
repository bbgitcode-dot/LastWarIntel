from types import SimpleNamespace

from ground_truth_validator import _count_evidence_by_field, _field_verified_by_reocr


def test_verified_display_counts_direct_character_evidence_field():
    evidence = [
        SimpleNamespace(field="player_name", status="verified_expected"),
        SimpleNamespace(field="player_name", status="verified_expected"),
        SimpleNamespace(field="alliance_tag", status="verified_expected"),
    ]

    assert _count_evidence_by_field(evidence, "player_name", "verified_expected") == 2
    assert _count_evidence_by_field(evidence, "alliance_tag", "verified_expected") == 1


def test_verified_display_resolution_accepts_all_local_expected_glyphs():
    assert _field_verified_by_reocr(
        already_exact=False,
        raw_target_count=2,
        local_target_count=2,
        skipped_target_count=0,
        verified_expected_count=2,
    )


def test_verified_display_resolution_blocks_skipped_nonlocal_glyphs():
    assert not _field_verified_by_reocr(
        already_exact=False,
        raw_target_count=3,
        local_target_count=2,
        skipped_target_count=1,
        verified_expected_count=2,
    )
