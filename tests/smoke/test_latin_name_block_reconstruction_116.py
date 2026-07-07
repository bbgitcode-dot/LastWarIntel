from pathlib import Path
from PIL import Image

from parser.targeted_character_reocr import (
    verify_latin_name_block_from_screenshot,
    _clean_latin_name_candidate,
)


class FakeReader:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = 0

    def read_rows(self, image):
        value = self.outputs[min(self.calls, len(self.outputs) - 1)]
        self.calls += 1
        return [([[0, 0], [10, 0], [10, 10], [0, 10]], value, 0.91)]


def test_latin_name_block_reconstructs_missing_glyph(tmp_path: Path):
    image_path = tmp_path / "screen.png"
    Image.new("RGB", (627, 915), "white").save(image_path)
    reader = FakeReader(["Mzzenmast", "Mizzenmast", "Mizzenmast", "Mizzenrnast"])

    evidence = verify_latin_name_block_from_screenshot(
        screenshot_path=image_path,
        expected_text="Mizzenmast",
        observed_text="Mzzenmast",
        row_slot=2,
        reader=reader,
    )

    assert evidence.status == "verified_expected"
    assert evidence.selected == "Mizzenmast"
    assert evidence.reason == "latin_name_block_reconstruction"
    assert evidence.crop_strategy == "latin_name_block"


def test_latin_name_block_rejects_non_latin_mixed_drift(tmp_path: Path):
    image_path = tmp_path / "screen.png"
    Image.new("RGB", (627, 915), "white").save(image_path)
    reader = FakeReader(["MEITTi X 叫@1"])

    evidence = verify_latin_name_block_from_screenshot(
        screenshot_path=image_path,
        expected_text="MEITTü メ 메잇",
        observed_text="MEITTi X 叫@1",
        row_slot=1,
        reader=reader,
    )

    assert evidence.status == "unresolved"
    assert evidence.reason == "latin_name_block_not_safe"
    assert reader.calls == 0


def test_latin_name_candidate_cleaning_removes_tags_and_power():
    assert _clean_latin_name_candidate("[PbC] Drpeek 271156279") == "Drpeek"
