"""OCR configuration for Sentinel.

EasyOCR language compatibility is limited: some languages cannot be loaded in
one shared reader. Sentinel therefore separates fast metadata OCR from optional
name OCR profiles.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class OCRProfile:
    """Concrete OCR reader configuration."""

    metadata_languages: tuple[str, ...]
    row_language_groups: tuple[tuple[str, ...], ...]


# Fast and stable. Recommended for normal transfer-baseline runs on CPU.
FAST_PROFILE = OCRProfile(
    metadata_languages=("en",),
    row_language_groups=(("en", "ch_sim"),),
)

# More complete but significantly slower on CPU. Use only for targeted review.
FULL_PROFILE = OCRProfile(
    metadata_languages=("en",),
    row_language_groups=(
        ("en", "ch_sim"),
        ("en", "ch_tra"),
        ("en", "ja"),
        ("en", "ko"),
    ),
)

_PROFILES = {
    "fast": FAST_PROFILE,
    "full": FULL_PROFILE,
}


def normalize_language_group(values: Iterable[str]) -> tuple[str, ...]:
    """Return normalized EasyOCR language names."""
    return tuple(str(value).strip() for value in values if str(value).strip())


def get_ocr_profile(profile_name: str | None = None) -> OCRProfile:
    """Return configured OCR profile.

    Environment variable:
        SENTINEL_OCR_PROFILE=fast|full

    Default is ``fast`` because metadata reliability and import speed are more
    important for baseline creation than speculative multilingual noise.
    """
    selected = (profile_name or os.getenv("SENTINEL_OCR_PROFILE") or "fast").strip().lower()
    if selected not in _PROFILES:
        raise ValueError(
            f"Unknown OCR profile '{selected}'. Supported profiles: {', '.join(sorted(_PROFILES))}."
        )
    return _PROFILES[selected]
