"""
Smoke Test
Multilingual OCR Configuration
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import parser.ocr as ocr  # noqa: E402


def main() -> None:
    assert ocr.get_ocr_languages() == ["en", "ch_sim", "ch_tra", "ja", "ko"]
    assert ocr.get_ocr_languages(["en", "ja"]) == ["en", "ja"]

    class FakeEasyOCR:
        calls = []

        @staticmethod
        def Reader(languages, gpu=False):
            FakeEasyOCR.calls.append((list(languages), gpu))
            return SimpleNamespace(languages=list(languages), gpu=gpu)

    sys.modules["easyocr"] = FakeEasyOCR
    try:
        reader = ocr.create_reader(gpu=False)
        assert reader.languages == ["en", "ch_sim", "ch_tra", "ja", "ko"]
        assert FakeEasyOCR.calls[-1] == (["en", "ch_sim", "ch_tra", "ja", "ko"], False)
    finally:
        sys.modules.pop("easyocr", None)

    print("PASS")


if __name__ == "__main__":
    main()
