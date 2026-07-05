from pathlib import Path

from PIL import Image

from parser.targeted_character_reocr import ReOcrTarget, _crop_box_variants, _field_box, verify_target_from_screenshot


class SequenceReader:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = 0

    def read_rows(self, _image):
        text = self.outputs[self.calls] if self.calls < len(self.outputs) else ""
        self.calls += 1
        return [([[0, 0], [1, 0], [1, 1], [0, 1]], text, 0.9)] if text else []


def test_110_alliance_tag_variants_start_with_full_tag_anchor():
    base = _field_box((633, 915), 0, "alliance_tag", text_length=3, position=1, field_text="PbC")
    variants = _crop_box_variants(base, (633, 915), ReOcrTarget("alliance_tag", 1, expected="b", observed="B", group="8Bb"))

    reasons = [reason for _box, reason in variants]
    assert reasons[:2] == ["tag_block_anchor", "tag_block_up_anchor"]
    assert "left_probe" in reasons
    assert "right_probe" in reasons


def test_110_full_tag_anchor_can_verify_pbc_case_before_noisy_glyphs(tmp_path: Path):
    screenshot = tmp_path / "screen.png"
    Image.new("RGB", (633, 915), "white").save(screenshot)
    reader = SequenceReader(["[PbC]", "内", "6", "h"])

    evidence = verify_target_from_screenshot(
        screenshot_path=screenshot,
        target=ReOcrTarget("alliance_tag", 1, expected="b", observed="B", group="8Bb"),
        expected_text="PbC",
        observed_text="PBC",
        row_slot=0,
        reader=reader,
    )

    assert evidence.status == "verified_expected"
    assert evidence.selected == "b"
    assert evidence.crop_candidate_reason == "tag_block_anchor"
    assert evidence.crop_anchor_status == "anchor_seen"
