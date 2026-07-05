from ground_truth_validator import _field_verified_by_reocr


def test_111_field_verified_by_reocr_requires_all_local_targets():
    assert _field_verified_by_reocr(
        already_exact=False,
        raw_target_count=2,
        local_target_count=2,
        skipped_target_count=0,
        verified_expected_count=2,
    )


def test_111_field_verified_by_reocr_refuses_skipped_nonlocal_targets():
    assert not _field_verified_by_reocr(
        already_exact=False,
        raw_target_count=3,
        local_target_count=1,
        skipped_target_count=2,
        verified_expected_count=1,
    )


def test_111_field_verified_by_reocr_keeps_already_exact_fields_gold_safe():
    assert _field_verified_by_reocr(
        already_exact=True,
        raw_target_count=0,
        local_target_count=0,
        skipped_target_count=0,
        verified_expected_count=0,
    )
