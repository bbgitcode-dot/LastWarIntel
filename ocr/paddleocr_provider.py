"""PaddleOCR provider implementation.

The import is intentionally lazy. PaddleOCR is an optional benchmark dependency.
If it is not installed, the benchmark records a provider error instead of
breaking the rest of Sentinel.
"""

from __future__ import annotations

import os
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
    # Keep initialization intentionally conservative.
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
    try:
        return [[float(point[0]), float(point[1])] for point in points]
    except Exception:
        return []


def _result_to_dict(result: Any) -> dict[str, Any] | None:
    """Normalize PaddleOCR v3 result objects into dictionaries.

    PaddleOCR 3.x returns rich result objects while PaddleOCR 2.x returns nested
    lists. Sentinel only needs bounding boxes, recognized text and confidence.
    This helper intentionally accepts several result shapes so the provider is
    resilient across PaddleOCR minor releases.
    """
    if isinstance(result, dict):
        return result

    for attr in ("json", "dict"):
        if hasattr(result, attr):
            value = getattr(result, attr)
            try:
                data = value() if callable(value) else value
            except TypeError:
                continue
            if isinstance(data, dict):
                return data

    if hasattr(result, "to_dict"):
        try:
            data = result.to_dict()
        except TypeError:
            data = None
        if isinstance(data, dict):
            return data

    return None


def _extract_from_dict(data: dict[str, Any]) -> list[OCRResult]:
    # Common PaddleOCR 3.x shape: {"res": {"rec_texts": ..., "rec_scores": ...}}
    res = data.get("res") if isinstance(data.get("res"), dict) else data
    texts = res.get("rec_texts") or res.get("texts") or res.get("text") or []
    scores = res.get("rec_scores") or res.get("scores") or []
    boxes = (
        res.get("rec_polys")
        or res.get("dt_polys")
        or res.get("rec_boxes")
        or res.get("boxes")
        or []
    )

    if isinstance(texts, str):
        texts = [texts]
    if not isinstance(texts, list):
        return []

    items: list[OCRResult] = []
    for idx, text in enumerate(texts):
        score = scores[idx] if isinstance(scores, list) and idx < len(scores) else 0.0
        box = boxes[idx] if isinstance(boxes, list) and idx < len(boxes) else []
        try:
            confidence = float(score)
        except (TypeError, ValueError):
            confidence = 0.0
        items.append((_as_box(box), str(text), confidence))
    return items


def _extract_items(raw: Any) -> Iterable[OCRResult]:
    """Yield PaddleOCR detections across common PaddleOCR result variants."""
    if raw is None:
        return []

    # PaddleOCR v3 commonly returns a list of result objects/dicts.
    if isinstance(raw, list) and raw:
        dict_items: list[OCRResult] = []
        for result in raw:
            data = _result_to_dict(result)
            if data:
                dict_items.extend(_extract_from_dict(data))
        if dict_items:
            return dict_items

    # PaddleOCR v2 commonly returns: [[box, (text, confidence)], ...]
    # or for a batch: [[[box, (text, confidence)], ...]]
    candidates = raw
    if isinstance(candidates, list) and len(candidates) == 1 and isinstance(candidates[0], list):
        if candidates[0] and isinstance(candidates[0][0], (list, tuple)):
            candidates = candidates[0]

    items: list[OCRResult] = []
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


def _run_paddle(reader: Any, image: Any) -> Any:
    """Run PaddleOCR across v2/v3 API variants.

    PaddleOCR 2.x exposes ``ocr`` and accepted ``cls``. PaddleOCR 3.x routes via
    ``predict`` and rejects ``cls``. Try modern APIs first, then legacy.
    """
    attempts = (
        lambda: reader.predict(image),
        lambda: reader.predict(input=image),
        lambda: reader.ocr(image),
    )
    last_error: Exception | None = None
    for attempt in attempts:
        try:
            return attempt()
        except TypeError as exc:
            last_error = exc
            continue
    if last_error:
        raise last_error
    return None


class PaddleOcrProvider:
    """Sentinel OCR provider backed by PaddleOCR."""

    def __init__(self, metadata_language: str | None = None, row_languages: tuple[str, ...] | None = None) -> None:
        self.metadata_language = metadata_language
        self.row_languages = row_languages

        resolved_metadata_language = metadata_language or os.getenv("SENTINEL_PADDLE_METADATA_LANG") or "en"
        resolved_row_languages = row_languages or _normalize_languages(
            os.getenv("SENTINEL_PADDLE_ROW_LANGS"),
            default=("ch", "chinese_cht", "japan", "korean"),
        )
        try:
            self.metadata_reader = _make_paddle_reader(resolved_metadata_language)
            self.row_readers = [_make_paddle_reader(language) for language in resolved_row_languages]
        except Exception as exc:  # pragma: no cover - optional dependency/models
            raise RuntimeError(
                "Failed to initialize PaddleOCR readers. "
                f"Metadata language: {resolved_metadata_language}. Row languages: {list(resolved_row_languages)}."
            ) from exc

        self._metadata_language = resolved_metadata_language
        self._row_languages = tuple(resolved_row_languages)

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
        raw = _run_paddle(reader, image)
        return list(_extract_items(raw))

    def read_metadata(self, image) -> list[OCRResult]:
        return self._read(self.metadata_reader, image)

    def read_rows(self, image) -> list[OCRResult]:
        all_results: list[OCRResult] = []
        for row_reader in self.row_readers:
            all_results.extend(self._read(row_reader, image))
        return deduplicate_ocr_results(all_results)
