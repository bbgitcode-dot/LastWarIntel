from parser.targeted_character_reocr import ReOcrTarget, filter_local_glyph_targets, verify_target_from_screenshot
from pathlib import Path


def test_115_keeps_missing_ascii_glyph_in_latin_name():
    targets = [
        ReOcrTarget("player_name", 1, expected="i", observed="", reason="display_character_difference"),
        ReOcrTarget("alliance_tag", 1, expected="b", observed="", group="8Bb"),
    ]

    filtered = filter_local_glyph_targets(
        targets,
        expected_name="Mizzenmast",
        observed_name="Mzzenmast",
        expected_alliance="PbC",
        observed_alliance="PC",
    )

    assert [(t.field, t.position, t.expected, t.observed) for t in filtered] == [
        ("player_name", 1, "i", ""),
        ("alliance_tag", 1, "b", ""),
    ]


def test_115_rejects_missing_unicode_glyph_in_mixed_name():
    targets = [
        ReOcrTarget("player_name", 13, expected="몽", observed="号", reason="display_character_difference"),
        ReOcrTarget("player_name", 14, expected="코", observed="卫", reason="display_character_difference"),
    ]

    assert filter_local_glyph_targets(
        targets,
        expected_name="Monkopeace x 몽코",
        observed_name="Monkopeace * 号卫",
    ) == []


def test_115_treats_latin_spacing_gap_as_verified_formatting():
    target = ReOcrTarget("player_name", 1, expected=" ", observed="", reason="display_character_difference")

    evidence = verify_target_from_screenshot(
        screenshot_path=Path("missing.png"),
        target=target,
        expected_text="N E R D",
        observed_text="NER0",
        row_slot=0,
        reader=None,
    )

    assert evidence.status == "verified_expected"
    assert evidence.selected == " "
    assert evidence.reason == "latin_spacing_gap"
