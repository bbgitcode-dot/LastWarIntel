"""Player name normalization for OCR-derived ranking validation.

This layer does not try to rewrite player names permanently. It produces a
comparison-friendly representation that is useful for validation and identity
scoring. The raw OCR name remains evidence; the normalized form is a derived
helper for fuzzy matching.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
import re
import unicodedata


_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_SPACE_RE = re.compile(r"\s+")
_LATIN_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'._-]*")
_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]")

# Common OCR confusions observed in Last War ranking screenshots. These are
# used only for comparison keys, never to mutate the stored raw name.
_TRANSLATION = str.maketrans({
    "0": "O",
    "1": "I",
    "l": "I",
    "|": "I",
    "2": "Z",
    "5": "S",
    "8": "B",
    "4": "A",
})

# Some OCR models output Han-like fragments for Hangul/Kana tails. Keep Latin
# identity cores measurable even when the CJK suffix is noisy.
_LATIN_CORE_MIN_LEN = 3


@dataclass(frozen=True)
class NameNormalizationResult:
    raw: str
    cleaned: str
    latin_core: str
    comparison_key: str
    corrections: list[str] = field(default_factory=list)


def _clean_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = _CONTROL_RE.sub("", text)
    text = text.replace("\u3000", " ")
    text = _SPACE_RE.sub(" ", text).strip()
    if text.lower() == "nan":
        return ""
    return text


def _strip_bracketed_tag(text: str) -> str:
    return re.sub(r"^\s*\[[A-Za-z0-9]{2,8}\]\s*", "", text).strip()


def _remove_badge_prefix(text: str) -> tuple[str, list[str]]:
    corrections: list[str] = []
    # Drop leading OCR debris before the first Latin token. This intentionally
    # does not remove leading CJK in names without a Latin component.
    match = _LATIN_TOKEN_RE.search(text)
    if match and match.start() > 0:
        prefix = text[: match.start()].strip()
        if prefix and not re.search(r"[A-Za-z0-9]{3,}", prefix):
            text = text[match.start():].strip()
            corrections.append("name_prefix_noise_removed")
    return text, corrections


def _latin_core(text: str) -> str:
    tokens = _LATIN_TOKEN_RE.findall(text)
    if not tokens:
        return ""
    # Ignore tiny UI fragments and keep readable Latin identity pieces.
    useful = [token for token in tokens if len(token) >= 2 or any(ch.isdigit() for ch in token)]
    if not useful:
        useful = tokens
    return " ".join(useful).strip()


def _comparison_key(text: str) -> str:
    key = text.upper().translate(_TRANSLATION)
    key = re.sub(r"[^A-Z0-9]+", "", key)
    return key


def normalize_player_name(value: object) -> NameNormalizationResult:
    raw = _clean_text(value)
    cleaned = _strip_bracketed_tag(raw)
    cleaned, corrections = _remove_badge_prefix(cleaned)
    cleaned = _SPACE_RE.sub(" ", cleaned).strip()
    latin = _latin_core(cleaned)
    key_source = latin if len(latin) >= _LATIN_CORE_MIN_LEN else cleaned
    key = _comparison_key(key_source)
    if latin and latin != cleaned:
        corrections.append("latin_core_extracted")
    return NameNormalizationResult(
        raw=raw,
        cleaned=cleaned,
        latin_core=latin,
        comparison_key=key,
        corrections=list(dict.fromkeys(corrections)),
    )


def normalized_name_similarity(expected: object, actual: object) -> float:
    expected_norm = normalize_player_name(expected)
    actual_norm = normalize_player_name(actual)

    if not expected_norm.comparison_key and not actual_norm.comparison_key:
        return 1.0
    if not expected_norm.comparison_key or not actual_norm.comparison_key:
        return 0.0

    key_similarity = SequenceMatcher(None, expected_norm.comparison_key, actual_norm.comparison_key).ratio()

    # For mixed Latin+CJK names, the Latin part is often the most stable identity
    # anchor. If both sides contain a meaningful Latin core, allow that to lift
    # the score, but never above exact-equivalent territory unless the full key
    # also agrees.
    latin_similarity = 0.0
    if expected_norm.latin_core and actual_norm.latin_core:
        left = _comparison_key(expected_norm.latin_core)
        right = _comparison_key(actual_norm.latin_core)
        if left and right:
            latin_similarity = SequenceMatcher(None, left, right).ratio()

    return round(max(key_similarity, latin_similarity * 0.95), 4)
