# Sentinel v0.9.5.13 - Player Name Normalization

## Added

- Player name normalization layer for OCR-derived ranking rows.
- Latin-core extraction for mixed Latin/CJK player names.
- OCR-confusion-aware comparison keys for identity validation.
- Ground Truth Validator metrics for normalized name similarity and normalized name matches.

## Changed

- `usable_identity_match` now considers both raw name similarity and normalized name similarity.
- Validation report now exposes normalized comparison artifacts:
  - `expected_name_latin_core`
  - `ocr_name_latin_core`
  - `expected_name_key`
  - `ocr_name_key`
  - `name_normalized_match`
  - `name_normalized_similarity`

## Impact

Against the Server 551 Top 50 Ground Truth dataset:

- Score improved from `56.71` to `60.54`.
- Usable identities improved from `21` to `23`.
- Normalized name matches added: `24`.

## Notes

The raw OCR name remains unchanged. Normalization is a derived validation and identity-comparison layer, not a destructive rewrite of player names.
