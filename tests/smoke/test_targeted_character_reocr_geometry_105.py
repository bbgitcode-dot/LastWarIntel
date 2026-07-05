from parser.targeted_character_reocr import _field_box


def test_105_joncollins_tail_digits_use_latin_pitch_not_power_column():
    box_two = _field_box((633, 915), 0, "player_name", text_length=len("Joncollins21"), position=10, field_text="Joncollins21")
    box_one = _field_box((633, 915), 0, "player_name", text_length=len("Joncollins21"), position=11, field_text="Joncollins21")

    # The .104 boxes were [398, 140, 426, 210] and [411, 140, 439, 210],
    # which hit the final `1`/empty space and leaked into non-name text.  The
    # .105 boxes are tighter, title-line only, and centered on the 2/1 tail.
    assert box_two[0] < 395
    assert box_two[2] <= 410
    assert box_one[0] < 405
    assert box_one[2] <= 420
    assert box_two[3] <= 185
    assert box_one[3] <= 185


def test_105_alliance_tag_middle_glyph_is_title_line_only():
    box = _field_box((633, 915), 0, "alliance_tag", text_length=3, position=1, field_text="PbC")

    # Narrow enough to target the middle `b`, and short enough to avoid the
    # lower Warzone line that confused EasyOCR in .104.
    assert 230 <= box[0] <= 236
    assert 241 <= box[2] <= 248
    assert box[3] <= 185
    assert (box[2] - box[0]) <= 14
