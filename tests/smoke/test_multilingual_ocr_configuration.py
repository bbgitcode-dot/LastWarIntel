"""Smoke test for configurable multilingual OCR setup."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from config.ocr import DEFAULT_OCR_LANGUAGES, get_ocr_languages  # noqa: E402
from parser.ocr import create_reader  # noqa: E402


def main() -> None:
    assert get_ocr_languages() == ["en", "ch_sim", "ch_tra", "ja", "ko"]
    assert DEFAULT_OCR_LANGUAGES == ["en", "ch_sim", "ch_tra", "ja", "ko"]
    assert get_ocr_languages({"ocr": {"languages": ["en", "ja"]}}) == ["en", "ja"]
    assert get_ocr_languages({"ocr_languages": ["en", "ko"]}) == ["en", "ko"]

    fake_easyocr = Mock()
    with patch("parser.ocr.importlib.import_module", return_value=fake_easyocr) as import_module:
        create_reader({"ocr": {"languages": ["en", "ja", "ko"]}})
        import_module.assert_called_once_with("easyocr")
        fake_easyocr.Reader.assert_called_once_with(["en", "ja", "ko"], gpu=False)

    print("PASS")


if __name__ == "__main__":
    main()
