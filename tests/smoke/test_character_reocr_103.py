from pathlib import Path
from PIL import Image
import json
import pandas as pd

from parser.targeted_character_reocr import ReOcrTarget, verify_target_from_screenshot
from ground_truth_validator import _flatten_character_reocr_debug


class FakeReader:
    def __init__(self, outputs):
        self.outputs = outputs
        self.calls = 0

    def read_rows(self, image):
        value = self.outputs[min(self.calls, len(self.outputs) - 1)]
        self.calls += 1
        return [([[0, 0], [10, 0], [10, 10], [0, 10]], value, 0.91)]


def test_window_screenshot_geometry_keeps_later_slots_on_correct_row(tmp_path: Path):
    image_path = tmp_path / "screen.png"
    Image.new("RGB", (627, 915), "white").save(image_path)
    reader = FakeReader(["[PbC]", "[PbC]", "[PbC]", "[PbC]"])
    evidence = verify_target_from_screenshot(
        screenshot_path=image_path,
        target=ReOcrTarget(field="alliance_tag", position=1, expected="b", observed="B", group="8Bb"),
        expected_text="PbC",
        observed_text="PBC",
        row_slot=2,
        reader=reader,
    )
    assert evidence.status == "verified_expected"
    assert evidence.crop_box is not None
    assert evidence.crop_box[1] >= 330  # .102 used ~260 here and read the previous row.
    assert evidence.crop_anchor_status == "anchor_seen"


def test_reocr_debug_surfaces_crop_field_mismatch():
    evidence = [{
        "field": "alliance_tag",
        "position": 1,
        "expected": "b",
        "observed": "B",
        "screenshot": "screen.png",
        "row_slot": 2,
        "crop_box": [208, 260, 263, 316],
        "status": "unresolved",
        "selected": "",
        "confidence": 0.0,
        "crop_strategy": "alliance_tag_position",
        "crop_anchor_status": "field_mismatch",
        "crop_anchor_text": "[IVE]",
        "crop_diagnostic": "crop_field_mismatch",
        "text_length": 3,
        "expected_text": "PbC",
        "observed_text": "PBC",
        "allowed_chars": "8Bb",
        "votes": [{"variant": "gray_x6", "text": "[IVE]", "confidence": 0.8, "char": ""}],
    }]
    detail = pd.DataFrame([{
        "server": 551,
        "rank": 3,
        "ocr_rank": 3,
        "expected_name": "Monkopeace x 몽코",
        "ocr_name": "Monkopeace * 号卫",
        "expected_alliance_display": "PbC",
        "ocr_alliance_display": "PBC",
        "expected_power": 317058104,
        "ocr_power": 317058104,
        "match_method": "server_power",
        "failure_class": "matched",
        "alignment_guard_status": "row_alignment_observed",
        "alignment_safe_for_character_verification": True,
        "character_verification_reasons": "case_sensitive_tag_difference",
        "character_reocr_evidence": json.dumps(evidence),
    }])
    debug = _flatten_character_reocr_debug(detail)
    row = debug.iloc[0]
    assert row["crop_anchor_status"] == "field_mismatch"
    assert row["crop_diagnostic"] == "crop_field_mismatch"
    assert row["debug_read"] == "crop_field_mismatch"
