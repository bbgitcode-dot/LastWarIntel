# Sentinel v0.9.5.12 - Alliance Normalization

## Added

- `parser/alliance_normalization.py`
- Vocabulary-aware alliance tag normalization.
- Conservative fuzzy correction for common OCR drops such as `PBC -> PC`, `IVE -> IV`, `PWW -> PW`.
- Ground Truth Validator now reports exact vs normalized alliance matches.

## Changed

- Player ranking export normalizes alliance tags using the local snapshot vocabulary.
- Ground Truth validation uses normalized alliance matches for identity usability.

## Why

The Ground Truth report showed many otherwise usable player rows failing because OCR dropped one character from short alliance tags. This patch treats alliance tags as entities with local context instead of raw OCR strings.
