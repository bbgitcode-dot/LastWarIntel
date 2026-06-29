"""PaddleOCR provider implementation.

The import is intentionally lazy. PaddleOCR is an optional benchmark dependency.
If it is not installed, the benchmark records a provider error instead of
breaking the rest of Sentinel.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterable

from ocr.provider import OCRResult, OcrProviderInfo
from ocr.utils import deduplicate_ocr_results


def _normalize_languages(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if not value:
        return default
    return tuple(part.strip() for part in value.split(",") if part.strip()) or default


def _make_paddle_reader(lang: str):
    try:
        from paddleocr import PaddleOCR  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "PaddleOCR is not installed. Install it with 'pip install paddleocr' "
            "before running the paddle benchmark."
        ) from exc

    # PaddleOCR has breaking constructor changes between releases.
    # v2 accepted show_log=False; newer v3 pipelines reject it.
    # Keep initialization intentionally conservative and retry with the
    # smallest compatible argument set before failing.
    attempts = (
        {"use_angle_cls": False, "lang": lang},
        {"lang": lang},
    )
    last_error = None
    for kwargs in attempts:
        try:
            return PaddleOCR(**kwargs)
        except (TypeError, ValueError) as exc:
            last_error = exc
            continue
    raise RuntimeError(f"Unable to initialize PaddleOCR for language {lang!r}: {last_error}")


def _as_box(points: Any) -> list[list[float]]:
    return [[float(point[0]), float(point[1])] for point in points]


def _extract_items(raw: Any) -> Iterable[tuple[Any, str, float]]:
    """Yield PaddleOCR detections across common PaddleOCR result variants."""
    if raw is None:
        return []

    # PaddleOCR v2 commonly returns: [[box, (text, confidence)], ...]
    # or for a batch: [[[box, (text, confidence)], ...]]
    candidates = raw
    if isinstance(candidates, list) and len(candidates) == 1 and isinstance(candidates[0], list):
        if candidates[0] and isinstance(candidates[0][0], (list, tuple)):
            candidates = candidates[0]

    items = []
    for item in candidates if isinstance(candidates, list) else []:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        box = item[0]
        payload = item[1]
        if isinstance(payload, (list, tuple)) and len(payload) >= 2:
            text = str(payload[0])
            try:
                confidence = float(payload[1])
            except (TypeError, ValueError):
                confidence = 0.0
            items.append((_as_box(box), text, confidence))
    return items


@dataclass(slots=True)
class PaddleOcrProvider:
    """Sentinel OCR provider backed by PaddleOCR."""

    metadata_language: str | None = None
    row_languages: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        metadata_language = self.metadata_language or os.getenv("SENTINEL_PADDLE_METADATA_LANG") or "en"
        row_languages = self.row_languages or _normalize_languages(
            os.getenv("SENTINEL_PADDLE_ROW_LANGS"),
            default=("ch", "chinese_cht", "japan", "korean"),
        )
        try:
            metadata_reader = _make_paddle_reader(metadata_language)
            row_readers = [_make_paddle_reader(language) for language in row_languages]
        except Exception as exc:  # pragma: no cover - optional dependency/models
            raise RuntimeError(
                "Failed to initialize PaddleOCR readers. "
                f"Metadata language: {metadata_language}. Row languages: {list(row_languages)}."
            ) from exc
        object.__setattr__(self, "_metadata_language", metadata_language)
        object.__setattr__(self, "_row_languages", tuple(row_languages))
        object.__setattr__(self, "metadata_reader", metadata_reader)
        object.__setattr__(self, "row_readers", row_readers)

    @property
    def info(self) -> OcrProviderInfo:
        return OcrProviderInfo(
            name="paddle",
            engine="PaddleOCR",
            metadata_languages=(self._metadata_language,),
            row_languages=self._row_languages,
            profile="benchmark",
        )

    @staticmethod
    def _read(reader: Any, image) -> list[OCRResult]:
        raw = reader.ocr(image, cls=False)
        return list(_extract_items(raw))

    def read_metadata(self, image) -> list[OCRResult]:
        return self._read(self.metadata_reader, image)

    def read_rows(self, image) -> list[OCRResult]:
        all_results: list[OCRResult] = []
        for row_reader in self.row_readers:
            all_results.extend(self._read(row_reader, image))
        return deduplicate_ocr_results(all_results)
