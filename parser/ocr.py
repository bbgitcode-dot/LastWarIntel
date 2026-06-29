"""OCR facade used by Sentinel's import pipeline.

Historically this module instantiated EasyOCR directly. It now delegates to an
exchangeable OCR provider while keeping the legacy function names used by
``main.py`` and older smoke tests.
"""

from __future__ import annotations

from ocr.provider import OCRResult, OcrProvider
from ocr.provider_factory import create_ocr_provider


SentinelOCRReader = OcrProvider


def create_reader(profile_name: str | None = None, provider_name: str | None = None) -> OcrProvider:
    """Create the configured OCR provider.

    Environment variables:
        SENTINEL_OCR_PROVIDER=easy|paddle
        SENTINEL_OCR_PROFILE=fast|full   (EasyOCR only)
    """
    return create_ocr_provider(provider_name=provider_name, profile_name=profile_name)


def read_metadata_ocr(reader: OcrProvider, image) -> list[OCRResult]:
    """Read screenshot metadata with the provider's metadata OCR mode."""
    return reader.read_metadata(image)


def read_ocr(reader: OcrProvider, image) -> list[OCRResult]:
    """Read ranking rows with the provider's row OCR mode."""
    return reader.read_rows(image)


def ocr_to_text(ocr_results: list[OCRResult]) -> str:
    return "\n".join([item[1] for item in ocr_results])
