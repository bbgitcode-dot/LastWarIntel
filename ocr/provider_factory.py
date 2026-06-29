"""Factory for exchangeable Sentinel OCR providers."""

from __future__ import annotations

import os

from ocr.provider import OcrProvider


def get_selected_provider_name(provider_name: str | None = None) -> str:
    return (provider_name or os.getenv("SENTINEL_OCR_PROVIDER") or "easy").strip().lower()


def create_ocr_provider(provider_name: str | None = None, profile_name: str | None = None) -> OcrProvider:
    selected = get_selected_provider_name(provider_name)
    if selected in {"easy", "easyocr"}:
        from ocr.easyocr_provider import EasyOcrProvider

        return EasyOcrProvider(profile_name=profile_name)
    if selected in {"paddle", "paddleocr"}:
        from ocr.paddleocr_provider import PaddleOcrProvider

        return PaddleOcrProvider()
    raise ValueError("Unknown OCR provider '%s'. Supported providers: easy, paddle." % selected)
