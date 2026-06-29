"""Exchangeable OCR providers for Sentinel."""

from ocr.provider import OCRResult, OcrProvider, OcrProviderInfo
from ocr.provider_factory import create_ocr_provider

__all__ = ["OCRResult", "OcrProvider", "OcrProviderInfo", "create_ocr_provider"]
