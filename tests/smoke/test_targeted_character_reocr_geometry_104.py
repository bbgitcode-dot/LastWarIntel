from pathlib import Path

from PIL import Image

from parser.targeted_character_reocr import (
    CharacterVote,
    ReOcrTarget,
    _classify_crop_anchor,
    _field_box,
    verify_target_from_screenshot,
)


class StubReader:
    def __init__(self, texts):
        self.texts = list(texts)
        self.calls = 0

    def read_rows(self, _image):
        text = self.texts[self.calls] if self.calls < len(self.texts) else ""
        self.calls += 1
        return [([[0, 0], [1, 0], [1, 1], [0, 1]], text, 0.9)] if text else []


def test_551_window_player_late_character_crop_stays_left_of_power_column():
    # v0.9.5.103 placed Joncollins position 10 around x=440-500 on a 627px
    # window screenshot, which leaked into the power column.  v0.9.5.104 keeps
    # the crop inside the identity column.
    box = _field_box((627, 915), 0, "player_name", text_length=len("Joncollins21"), position=10, field_text="Joncollins21")

    assert box[2] <= 450
    assert box[0] < box[2]


def test_551_window_alliance_middle_glyph_crop_is_tight_and_left_shifted():
    # The middle b in [PbC] must not be cropped as the C/right bracket area.
    box = _field_box((627, 915), 0, "alliance_tag", text_length=3, position=1, field_text="PbC")

    assert box[0] < 230
    assert box[2] < 270
    assert (box[2] - box[0]) <= 35


def test_player_crop_digit_text_is_classified_as_power_column_bleed():
    votes = [CharacterVote("gray_x6", "286", 0.9, ""), CharacterVote("contrast_x6", "320", 0.8, "")]

    status, text, diagnostic = _classify_crop_anchor(
        votes,
        ReOcrTarget("player_name", 8, expected="G", observed="6", group="6G"),
        "Pumpkin G",
        "Pumpkin 6",
    )

    assert status == "field_mismatch"
    assert diagnostic == "crop_power_column_bleed"
    assert "286" in text


def test_tighter_player_crop_can_verify_joncollins_expected_digit(tmp_path: Path):
    screenshot = tmp_path / "screen.png"
    Image.new("RGB", (627, 915), "white").save(screenshot)
    reader = StubReader(["2", "2", "2", "2"])

    evidence = verify_target_from_screenshot(
        screenshot_path=screenshot,
        target=ReOcrTarget("player_name", 10, expected="2", observed="z", group="2zZ"),
        expected_text="Joncollins21",
        observed_text="Joncollinszl",
        row_slot=0,
        reader=reader,
    )

    assert evidence.status == "verified_expected"
    assert evidence.selected == "2"
    assert evidence.crop_box is not None
    assert evidence.crop_box[2] <= 450
