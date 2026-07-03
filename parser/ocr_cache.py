"""Persistent OCR cache for Sentinel import runs.

The cache is a development and runtime optimization only. It stores OCR sensor
observations keyed by file content hash, OCR provider fingerprint, OCR mode and
image normalization parameters. Cached OCR must never be treated as business
truth; it is simply the same observation reused to avoid reading identical
screenshots again.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ocr.provider import OCRResult, OcrProvider

DEFAULT_CACHE_DIR = Path("data/ocr_cache")
CACHE_SCHEMA = "sentinel.ocr_cache.v1"


def _jsonable(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return _jsonable(value.tolist())
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _serialize_results(results: list[OCRResult]) -> list[list[Any]]:
    serialized: list[list[Any]] = []
    for box, text, confidence in results:
        try:
            conf = float(confidence)
        except (TypeError, ValueError):
            conf = 0.0
        serialized.append([_jsonable(box), str(text), conf])
    return serialized


def _deserialize_results(payload: Any) -> list[OCRResult]:
    results: list[OCRResult] = []
    if not isinstance(payload, list):
        return results
    for item in payload:
        if not isinstance(item, list) or len(item) < 3:
            continue
        box, text, confidence = item[0], item[1], item[2]
        try:
            conf = float(confidence)
        except (TypeError, ValueError):
            conf = 0.0
        results.append((box, str(text), conf))
    return results


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def provider_fingerprint(reader: OcrProvider) -> str:
    info = reader.info
    parts = [
        info.engine,
        info.name,
        info.profile,
        ",".join(info.metadata_languages),
        ",".join(info.row_languages),
    ]
    raw = "|".join(str(part) for part in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def cache_key(*, screenshot: Path, reader: OcrProvider, mode: str, target_width: int, target_height: int) -> str:
    raw = "|".join([
        CACHE_SCHEMA,
        file_sha256(screenshot),
        provider_fingerprint(reader),
        str(mode),
        str(target_width),
        str(target_height),
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass
class OcrCacheStats:
    hits: int = 0
    misses: int = 0
    writes: int = 0
    errors: int = 0

    def as_dict(self) -> dict[str, int]:
        return {"hits": self.hits, "misses": self.misses, "writes": self.writes, "errors": self.errors}


class OcrCache:
    def __init__(self, cache_dir: Path | str = DEFAULT_CACHE_DIR, *, enabled: bool = True):
        self.cache_dir = Path(cache_dir)
        self.enabled = enabled
        self.stats = OcrCacheStats()
        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get_or_compute(
        self,
        *,
        screenshot: Path,
        reader: OcrProvider,
        image: Any,
        mode: str,
        target_width: int,
        target_height: int,
        compute: Callable[[OcrProvider, Any], list[OCRResult]],
    ) -> list[OCRResult]:
        if not self.enabled:
            self.stats.misses += 1
            return compute(reader, image)

        try:
            key = cache_key(
                screenshot=screenshot,
                reader=reader,
                mode=mode,
                target_width=target_width,
                target_height=target_height,
            )
            path = self._path(key)
            if path.exists():
                payload = json.loads(path.read_text(encoding="utf-8"))
                if payload.get("schema") == CACHE_SCHEMA and payload.get("mode") == mode:
                    self.stats.hits += 1
                    return _deserialize_results(payload.get("results"))
            self.stats.misses += 1
            results = compute(reader, image)
            payload = {
                "schema": CACHE_SCHEMA,
                "mode": mode,
                "source_file": screenshot.name,
                "source_sha256": file_sha256(screenshot),
                "provider": provider_fingerprint(reader),
                "target_width": target_width,
                "target_height": target_height,
                "results": _serialize_results(results),
            }
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            self.stats.writes += 1
            return results
        except Exception:
            # Cache failures must never block imports or change data decisions.
            self.stats.errors += 1
            return compute(reader, image)
