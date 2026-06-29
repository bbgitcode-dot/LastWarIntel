"""OCR provider interface for Sentinel.

OCR is treated as an exchangeable observation sensor. Providers return
EasyOCR-compatible tuples so the existing parser can remain unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


OCRBox = Any
OCRResult = tuple[OCRBox, str, float]


@dataclass(frozen=True)
class OcrProviderInfo:
    """Human-readable metadata for benchmark and runtime reports."""

    name: str
    engine: str
    metadata_languages: tuple[str, ...]
    row_languages: tuple[str, ...]
    profile: str


class OcrProvider(Protocol):
    """Common contract implemented by all OCR engines."""

    @property
    def info(self) -> OcrProviderInfo:
        """Return provider metadata."""

    def read_metadata(self, image) -> list[OCRResult]:
        """Read screenshot metadata such as Warzone and ranking type."""

    def read_rows(self, image) -> list[OCRResult]:
        """Read ranking rows and player/alliance names."""
