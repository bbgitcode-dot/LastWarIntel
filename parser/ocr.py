"""
OCR adapter for Sentinel.

The OCR layer converts screenshots into raw text observations. It must not
contain domain logic. Language configuration is intentionally centralized so
transfer-baseline runs can be optimized without code changes.
"""

from __future__ import annotations

import os
from typing import Iterable, List, Optional, Sequence

try:
    from config.ocr import DEFAULT_OCR_LANGUAGES, OCR_GPU
except Exception:  # pragma: no cover - defensive fallback for partial installs
    DEFAULT_OCR_LANGUAGES = ["en", "ch_sim", "ch_tra", "ja", "ko"]
    OCR_GPU = False


ENV_LANGUAGES = "SENTINEL_OCR_LANGUAGES"
ENV_GPU = "SENTINEL_OCR_GPU"


def _split_languages(value: str) -> List[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def get_ocr_languages(languages: Optional[Sequence[str]] = None) -> List[str]:
    """Return the configured OCR languages in deterministic order.

    Priority:
    1. Explicit function argument
    2. SENTINEL_OCR_LANGUAGES environment variable, comma-separated
    3. config.ocr.DEFAULT_OCR_LANGUAGES
    """

    if languages is not None:
        cleaned = [str(lang).strip() for lang in languages if str(lang).strip()]
        return cleaned or ["en"]

    env_value = os.getenv(ENV_LANGUAGES, "").strip()
    if env_value:
        parsed = _split_languages(env_value)
        if parsed:
            return parsed

    return list(DEFAULT_OCR_LANGUAGES)


def get_ocr_gpu(default: bool = OCR_GPU) -> bool:
    """Return OCR GPU setting, allowing environment override."""

    env_value = os.getenv(ENV_GPU, "").strip().lower()
    if env_value in {"1", "true", "yes", "y", "on"}:
        return True
    if env_value in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def create_reader(
    languages: Optional[Sequence[str]] = None,
    gpu: Optional[bool] = None,
    *,
    allow_english_fallback: bool = True,
):
    """Create an EasyOCR reader using Sentinel's configured languages.

    The default language set supports English, simplified/traditional Chinese,
    Japanese and Korean. If EasyOCR cannot initialize the multilingual reader
    because models are missing or unsupported, Sentinel falls back to English
    by default and prints a clear warning instead of failing silently.
    """

    selected_languages = get_ocr_languages(languages)
    use_gpu = get_ocr_gpu() if gpu is None else bool(gpu)

    try:
        import easyocr
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on runtime
        raise RuntimeError(
            "EasyOCR is not installed. Install it before running OCR imports."
        ) from exc

    try:
        return easyocr.Reader(selected_languages, gpu=use_gpu)
    except Exception as exc:
        if not allow_english_fallback or selected_languages == ["en"]:
            raise RuntimeError(
                f"Failed to initialize EasyOCR with languages {selected_languages}."
            ) from exc

        print(
            "WARNING: Failed to initialize EasyOCR with languages "
            f"{selected_languages}. Falling back to ['en']. Original error: {exc}"
        )
        return easyocr.Reader(["en"], gpu=use_gpu)


def read_ocr(reader, image):
    return reader.readtext(image, detail=1, paragraph=False)


def ocr_to_text(ocr_results):
    return "\n".join([item[1] for item in ocr_results])
