# Sentinel v0.9.5.9 – Row Alignment Engine

## Added

- Bounding-box based row alignment engine in `parser/alignment.py`.
- Layout-aware THP row reconstruction using power values as row anchors.
- Rank-token pairing by nearest Y position.
- Row bands based on neighbouring power anchors.
- Alignment warnings for missing rank anchors and empty reconstructed names.
- Smoke tests for row-shift prevention.

## Changed

- `parse_ranking_rows()` no longer relies on broad OCR text clustering as the primary parser strategy.
- Parsed rows preserve visual order before final merge/debugging.
- Existing ranking merge keeps alignment warnings in `rank_warning` so suspicious rows remain visible in Excel.

## Rationale

Ground-truth validation for Server 551 showed that low name accuracy was largely caused by row reconstruction drift rather than pure OCR failure. The new alignment engine treats OCR output as positioned layout evidence first and text second.

## Expected Impact

- Fewer cases where one player's name is assigned to the next player's power.
- Better name, alliance, and power consistency against ground truth.
- Cleaner foundation for future identity matching and Joiner/Leaver detection.
