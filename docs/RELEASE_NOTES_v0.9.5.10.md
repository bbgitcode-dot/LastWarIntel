# Sentinel v0.9.5.10 – Power-First Ranking Reconstruction

## Added

- Power-first ranking reconstruction rule for THP exports.
- Ground Truth validation now prefers exact THP power matches before rank matches.

## Changed

- Exported `rank` is now the computed power-order rank.
- OCR rank remains available as `ocr_rank` evidence and produces warnings when it differs from the power-order rank.
- Rank warnings now distinguish OCR-rank mismatch from final computed rank.

## Why

Ground Truth validation showed that OCR rank tokens can be shifted or duplicated. THP values are much more stable and uniquely identify visible ranking rows. Sentinel therefore treats power as the primary reconstruction anchor and rank as supporting evidence.
