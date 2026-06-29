# Sentinel v0.9.5.11 – Column Reconstruction Engine

## Added

- `parser/columns.py` with token-level column reconstruction for THP ranking rows.
- Column-aware extraction for `rank | alliance | player_name | power` after row alignment.
- Repair for malformed alliance tags such as `IPbC]` → `[PbC]`.
- Badge/noise filtering for OCR fragments before the alliance column.
- Column correction metadata exported through parser rows.
- Smoke tests for column reconstruction edge cases.

## Changed

- `parse_ranking_rows()` now delegates row-internal field extraction to the Column Reconstruction Engine.
- Player ranking builder preserves column-level corrections in parse corrections.

## Why

Power-first reconstruction improved row matching. The next bottleneck was field extraction inside each row: badge noise, malformed alliance brackets, and combined tag/name OCR tokens. This release separates row detection from column interpretation so future identity normalization can operate on cleaner structured fields.
