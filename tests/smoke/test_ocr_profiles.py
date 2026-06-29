from config.ocr import get_ocr_profile


def test_fast_ocr_profile_uses_stable_metadata_reader():
    profile = get_ocr_profile("fast")
    assert profile.metadata_languages == ("en",)
    assert profile.row_language_groups == (("en", "ch_sim"),)


def test_full_ocr_profile_splits_easyocr_incompatible_languages():
    profile = get_ocr_profile("full")
    assert ("en", "ch_tra") in profile.row_language_groups
    assert ("en", "ja") in profile.row_language_groups
    assert ("en", "ko") in profile.row_language_groups
    assert all("en" in group for group in profile.row_language_groups)
