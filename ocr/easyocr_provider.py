"""EasyOCR provider implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config.ocr import OCRProfile, get_ocr_profile
from ocr.provider import OCRResult, OcrProviderInfo
from ocr.utils import deduplicate_ocr_results


def _make_easyocr_reader(languages: tuple[str, ...]):
    # Import lazily so tests and non-EasyOCR benchmark code can import the
    # provider package even when EasyOCR is not installed.
    import easyocr  # type: ignore

    return easyocr.Reader(list(languages), gpu=False)


@dataclass(slots=True)
class EasyOcrProvider:
    """Sentinel OCR provider backed by EasyOCR."""

    profile_name: str | None = None

    def __post_init__(self) -> None:
        profile = get_ocr_profile(self.profile_name)
        object.__setattr__(self, "profile", profile)
        try:
            metadata_reader = _make_easyocr_reader(profile.metadata_languages)
            row_readers = [_make_easyocr_reader(group) for group in profile.row_language_groups]
        except Exception as exc:  # pragma: no cover - depends on local OCR install/models
            raise RuntimeError(
                "Failed to initialize EasyOCR readers. "
                f"Metadata languages: {list(profile.metadata_languages)}. "
                f"Row language groups: {[list(group) for group in profile.row_language_groups]}. "
                "Use SENTINEL_OCR_PROFILE=fast for the stable CPU baseline profile."
            ) from exc
        object.__setattr__(self, "metadata_reader", metadata_reader)
        object.__setattr__(self, "row_readers", row_readers)

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
