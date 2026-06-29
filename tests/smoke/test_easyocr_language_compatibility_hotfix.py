from config.ocr import get_ocr_language_groups, DEFAULT_OCR_LANGUAGE_GROUPS
from parser.ocr import merge_ocr_results


def test_default_languages_are_split_into_easyocr_compatible_groups():
    assert DEFAULT_OCR_LANGUAGE_GROUPS == [
        ["en", "ch_sim"],
        ["en", "ch_tra"],
        ["en", "ja"],
        ["en", "ko"],
    ]
    assert get_ocr_language_groups() == DEFAULT_OCR_LANGUAGE_GROUPS


def test_flat_language_config_is_converted_to_safe_groups():
    config = {"ocr": {"languages": ["en", "ja", "ko"]}}
    assert get_ocr_language_groups(config) == [["en", "ja"], ["en", "ko"]]


def test_duplicate_ocr_regions_are_merged_by_confidence():
    low = ([[0, 0], [10, 0], [10, 10], [0, 10]], "Warzone #540", 0.4)
    high = ([[1, 1], [11, 1], [11, 11], [1, 11]], "Warzone #549", 0.9)
    merged = merge_ocr_results([low, high])
    assert len(merged) == 1
    assert merged[0][1] == "Warzone #549"
