# Patch Summary – v0.9.5.96

## Sentinel v0.9.5.96 – 551 Gold Fidelity Gate

This sprint tightens Sentinel around the immediate goal agreed with the Proud Owner: one server must become a trustworthy Gold Run before wider entity intelligence or full-scope acquisition matters. Runtime and cache remain secondary. OCR cache stays disabled for validation unless explicitly requested.

## Implemented

- Added Gold Fidelity summary metrics to the Ground Truth Validator.
- Added `gold_fidelity_ready` and `gold_fidelity_blocker_rows`.
- Added explicit blocker counts for player-name display drift, alliance-tag display drift, power drift and rank drift.
- Added a dedicated `gold_fidelity_blockers` sheet and JSON section.
- Refined Character Verification planning so stable-but-confusable characters are not counted as blockers by default.
- Kept alliance tags case-sensitive: `PbC` is not `PBC`; `DAY` is not `daY`.

## Validation

- Character verification smoke tests: passed.
- Validator discipline smoke tests: passed.
- 551 Ground Truth Validator run against current export: completed.
- py_compile: passed for touched files.

## Current 551 Gold Status

The current 551 benchmark still is **not Gold-ready**. It has 100% recall and 0 bad matches, but 44 Gold Fidelity blockers remain. The patch makes those blockers explicit instead of hiding them behind usable/fuzzy identity matches.

## Version

`0.9.5.96`
