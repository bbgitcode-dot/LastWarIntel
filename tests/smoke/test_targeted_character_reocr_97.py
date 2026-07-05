from pathlib import Path
from PIL import Image

from parser.targeted_character_reocr import (
    ReOcrTarget,
    parse_reocr_targets,
    verify_target_from_screenshot,
    summarize_evidence,
)


class FakeReader:
    def __init__(self, outputs):
        self.outputs = outputs
        self.calls = 0

    def read_rows(self, image):
        value = self.outputs[min(self.calls, len(self.outputs) - 1)]
        self.calls += 1
        return [([[0, 0], [10, 0], [10, 10], [0, 10]], value, 0.91)]


def test_parse_reocr_targets_from_validator_json():
    targets = parse_reocr_targets('[{"field":"player_name","position":10,"expected":"2","observed":"z","reason":"same_confusion_family_difference","group":"2zZ"}]')
    assert len(targets) == 1
    assert targets[0].expected == "2"
    assert targets[0].observed == "z"


def test_targeted_reocr_votes_for_expected_character(tmp_path: Path):
    image_path = tmp_path / "screen.png"
    Image.new("RGB", (600, 1064), "white").save(image_path)
    reader = FakeReader(["2", "2", "z", "2"])
    evidence = verify_target_from_screenshot(
        screenshot_path=image_path,
        target=ReOcrTarget(field="player_name", position=10, expected="2", observed="z"),
        expected_text="Joncollins21",
        observed_text="Joncollinszl",
        row_slot=0,
        reader=reader,
    )
    assert evidence.status == "verified_expected"
    assert evidence.selected == "2"
    assert evidence.confidence >= 0.55


def test_targeted_reocr_without_reader_is_unresolved(tmp_path: Path):
    image_path = tmp_path / "screen.png"
    Image.new("RGB", (600, 1064), "white").save(image_path)
    evidence = verify_target_from_screenshot(
        screenshot_path=image_path,
        target=ReOcrTarget(field="alliance_tag", position=1, expected="b", observed="B"),
        expected_text="PbC",
        observed_text="PBC",
        row_slot=0,
        reader=None,
    )
    assert evidence.status == "unresolved"
    assert summarize_evidence([evidence])["unresolved"] == 1


def test_alliance_tag_vote_uses_requested_tag_position(tmp_path: Path):
    image_path = tmp_path / "screen.png"
    Image.new("RGB", (600, 1064), "white").save(image_path)
    reader = FakeReader(["[PbC]", "[PC]", "[PBC]", "[PbC]"])
    evidence = verify_target_from_screenshot(
        screenshot_path=image_path,
        target=ReOcrTarget(field="alliance_tag", position=1, expected="b", observed="B", group="8Bb"),
        expected_text="PbC",
        observed_text="PBC",
        row_slot=0,
        reader=reader,
    )
    assert evidence.selected == "b"
    assert evidence.status == "verified_expected"


def test_non_target_noise_is_unresolved_not_ambiguous(tmp_path: Path):
    image_path = tmp_path / "screen.png"
    Image.new("RGB", (600, 1064), "white").save(image_path)
    reader = FakeReader(["[IVE]", "[PC]", "???", ""])
    evidence = verify_target_from_screenshot(
        screenshot_path=image_path,
        target=ReOcrTarget(field="player_name", position=10, expected="2", observed="z", group="2zZ"),
        expected_text="Joncollins21",
        observed_text="Joncollinszl",
        row_slot=0,
        reader=reader,
    )
    assert evidence.status == "unresolved"
    assert evidence.selected == ""
