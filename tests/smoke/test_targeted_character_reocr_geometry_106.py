from pathlib import Path

from PIL import Image

from parser.targeted_character_reocr import (
    ReOcrTarget,
    _crop_box_variants,
    _field_box,
    verify_target_from_screenshot,
)


class SequenceReader:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = 0

    def read_rows(self, _image):
        text = self.outputs[self.calls] if self.calls < len(self.outputs) else ""
        self.calls += 1
        return [([[0, 0], [1, 0], [1, 1], [0, 1]], text, 0.9)] if text else []


def test_106_visible_window_crops_start_above_title_baseline():
    box = _field_box((633, 915), 0, "player_name", text_length=len("Joncollins21"), position=10, field_text="Joncollins21")

    # .105 started at y=140 and missed the top half of the orange glyphs.  .106
    # moves the crop back onto the title line without including Warzone #551.
    assert box[1] <= 126
    assert box[3] <= 175


def test_106_generates_calibration_offsets_for_empty_base_crop():
    base = _field_box((633, 915), 0, "player_name", text_length=len("Joncollins21"), position=10, field_text="Joncollins21")
    variants = _crop_box_variants(base, (633, 915), ReOcrTarget("player_name", 10, expected="2", observed="z", group="2zZ"))

    assert len(variants) >= 5
    assert any(reason == "left_wide" for _box, reason in variants)
    assert any(reason == "right_wide" for _box, reason in variants)
    assert any(box[1] < base[1] for box, _reason in variants)


def test_106_fallback_candidate_can_verify_when_base_is_empty(tmp_path: Path):
    screenshot = tmp_path / "screen.png"
    Image.new("RGB", (633, 915), "white").save(screenshot)
    # First four OCR calls are the base crop variants; the next calibrated crop
    # sees the expected character.  This models Joncollins where the fixed crop
    # can be empty but a nearby candidate contains the tail glyph.
    reader = SequenceReader(["", "", "", "", "2", "2", "2", "2"])

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
    assert evidence.crop_candidate_count > 1
    assert evidence.crop_candidate_reason != "base"
