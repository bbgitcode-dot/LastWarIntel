from parser.name_normalization import normalize_player_name, normalized_name_similarity


def test_common_ocr_digit_letter_confusions_are_comparable():
    assert normalized_name_similarity("Joncollins21", "Joncollinszl") >= 0.80
    assert normalized_name_similarity("Sc4rfac3", "Scyrfac3") >= 0.80
    assert normalized_name_similarity("97 McJesus", "97 Mclesus") >= 0.80


def test_latin_core_keeps_mixed_names_usable_when_cjk_suffix_is_noisy():
    assert normalized_name_similarity("Wowamonkey 브로", "Wowamonkey 些呈") >= 0.80
    assert normalized_name_similarity("Moist Tuna 참치", "Moist Tuna 升") >= 0.80


def test_missing_name_does_not_match():
    assert normalized_name_similarity("P8n", "") == 0.0


def test_badge_prefix_is_removed_from_latin_core():
    normalized = normalize_player_name('铟 四咆鹪E [W叫u] Pbeachhead x "u')
    assert "Pbeachhead" in normalized.latin_core
