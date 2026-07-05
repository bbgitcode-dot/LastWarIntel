from parser.targeted_character_reocr import ReOcrTarget, filter_local_glyph_targets, is_local_glyph_target


def test_109_keeps_joncollins_tail_confusables():
    targets = [
        ReOcrTarget("player_name", 10, expected="2", observed="z", group="2zZ"),
        ReOcrTarget("player_name", 11, expected="1", observed="l", group="1lI|"),
        ReOcrTarget("alliance_tag", 1, expected="b", observed="B", group="8Bb"),
    ]

    filtered = filter_local_glyph_targets(
        targets,
        expected_name="Joncollins21",
        observed_name="Joncollinszl",
        expected_alliance="PbC",
        observed_alliance="PBC",
    )

    assert [(t.field, t.position, t.expected, t.observed) for t in filtered] == [
        ("player_name", 10, "2", "z"),
        ("player_name", 11, "1", "l"),
        ("alliance_tag", 1, "b", "B"),
    ]


def test_109_rejects_broad_unicode_display_drift_as_nonlocal():
    targets = [
        ReOcrTarget("player_name", 7, expected="メ", observed="X", reason="display_character_difference"),
        ReOcrTarget("player_name", 9, expected="메", observed="叫", reason="display_character_difference"),
        ReOcrTarget("player_name", 10, expected="", observed="1", group="1lI|"),
    ]

    filtered = filter_local_glyph_targets(
        targets,
        expected_name="MEITTü メ 메잇",
        observed_name="MEITTi X 叫@1",
    )

    assert filtered == []


def test_109_keeps_ascii_case_glyph_but_not_empty_insertions():
    assert is_local_glyph_target(ReOcrTarget("player_name", 0, expected="x", observed="X"))
    assert not is_local_glyph_target(ReOcrTarget("player_name", 4, expected="", observed="0", group="0Oo"))
