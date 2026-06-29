"""EasyOCR provider implementation."""

from __future__ import annotations

from typing import Any

from config.ocr import get_ocr_profile
from ocr.provider import OCRResult, OcrProviderInfo
from ocr.utils import deduplicate_ocr_results


def _make_easyocr_reader(languages: tuple[str, ...]):
    # Import lazily so tests and non-EasyOCR benchmark code can import the
    # provider package even when EasyOCR is not installed.
    import easyocr  # type: ignore

    return easyocr.Reader(list(languages), gpu=False)


class EasyOcrProvider:
    """Sentinel OCR provider backed by EasyOCR.

    This class intentionally does not use ``@dataclass(slots=True)``.
    OCR readers and profile metadata are runtime state and must be set during
    initialization. A slotted dataclass caused AttributeError when the provider
    architecture attempted to attach those attributes.
    """

    def __init__(self, profile_name: str | None = None) -> None:
        self.profile_name = profile_name
        self.profile = get_ocr_profile(profile_name)
        try:
            self.metadata_reader = _make_easyocr_reader(self.profile.metadata_languages)
            self.row_readers = [_make_easyocr_reader(group) for group in self.profile.row_language_groups]
        except Exception as exc:  # pragma: no cover - depends on local OCR install/models
            raise RuntimeError(
                "Failed to initialize EasyOCR readers. "
                f"Metadata languages: {list(self.profile.metadata_languages)}. "
                f"Row language groups: {[list(group) for group in self.profile.row_language_groups]}. "
                "Use SENTINEL_OCR_PROFILE=fast for the stable CPU baseline profile."
            ) from exc

    @property
    def info(self) -> OcrProviderInfo:
        row_languages = tuple(dict.fromkeys(lang for group in self.profile.row_language_groups for lang in group))
        return OcrProviderInfo(
            name="easy",
            engine="EasyOCR",
            metadata_languages=self.profile.metadata_languages,
            row_languages=row_languages,
            profile=self.profile_name or "fast",
        )

    @staticmethod
    def _read(reader: Any, image) -> list[OCRResult]:
        return reader.readtext(image, detail=1, paragraph=False)

    def read_metadata(self, image) -> list[OCRResult]:
        return self._read(self.metadata_reader, image)

    def read_rows(self, image) -> list[OCRResult]:
        all_results: list[OCRResult] = []
        for row_reader in self.row_readers:
            all_results.extend(self._read(row_reader, image))
        return deduplicate_ocr_results(all_results)
