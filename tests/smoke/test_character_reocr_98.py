from pathlib import Path
import tempfile
import zipfile

import pandas as pd
from PIL import Image

from ground_truth_validator import _discover_screenshots_dir, validate


def test_zip_screenshot_discovery_extracts_zip():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        png = root / "shot.png"
        Image.new("RGB", (20, 20), "white").save(png)
        zip_path = root / "551.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.write(png, arcname="shot.png")

        discovered, handle, kind = _discover_screenshots_dir(str(zip_path), root / "output.xlsx")
        try:
            assert kind == "zip"
            assert discovered is not None
            assert (discovered / "shot.png").exists()
        finally:
            if handle is not None:
                handle.cleanup()


def test_character_reocr_targets_are_emitted_without_provider_when_screenshot_exists():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        screenshot_dir = root / "screenshots"
        screenshot_dir.mkdir()
        Image.new("RGB", (600, 1064), "white").save(screenshot_dir / "screen.png")

        gt = pd.DataFrame([
            {"server": 551, "rank": 1, "alliance": "PbC", "alliance_display": "PbC", "power": 416693161, "true_name": "Joncollins21", "screenshot": "screen.png", "name_category": "latin_only"}
        ])
        ocr = pd.DataFrame([
            {"server": 551, "rank": 1, "alliance": "PBC", "alliance_display": "PBC", "power": 416693161, "ocr_name": "Joncollinszl", "source_file": "screen.png", "ocr_sheet": "551_total_hero_power"}
        ])

        summary, detail, _category = validate(gt, ocr, pd.DataFrame(), character_reocr_reader=None, screenshots_dir=screenshot_dir)

        assert summary.character_verification_candidate_rows == 1
        assert summary.character_reocr_target_count == 3
        assert summary.character_reocr_unresolved == 3
        assert detail.iloc[0]["character_reocr_status"] == "unresolved"
