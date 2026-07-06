# Changelog

## v0.9.5.73 – Snapshot Upload Binding & Import Context Enforcement

- Enforced active `screenshot_upload` snapshot before screenshot imports.
- Bound latest import report, generated exports and review history to the active snapshot.
- Added Import Center snapshot coverage with expected/imported/missing feed visibility.
- Added smoke tests for snapshot context enforcement.


## [0.9.5.72] - Documentation Consolidation & Project Handover

### Added
- Added `docs/NEXT_CHAT.md` with complete next-chat handoff instructions.
- Added official Snapshot Management roadmap and lifecycle documentation across core docs.
- Added explicit project philosophy: Data Quality before Intelligence.

### Changed
- Consolidated release notes into `docs/RELEASE_NOTES.md`.
- Consolidated patch summaries into `docs/PATCH_SUMMARY.md`.
- Updated `PROJECT_STATUS.md`, `ROAD_TO_V1.md`, `MODUS_OPERANDI.md`, `ARCHITECTURE.md`, `ARCHITECTURAL_DECISIONS.md`, `LESSONS_LEARNED.md`, `SENTINEL_DATA_GUARD.md` and docs index.
- Clarified separation between Current Run, Historical Dataset, Benchmark/Ground Truth, Review History and Operational Truth.

### Safety
- Documentation-only release. No runtime behavior changes.

## [0.9.5.71] - Snapshot Management Foundation

### Added
- Managed snapshot foundation for human-named import context.
- Import Center snapshot controls.
- Active snapshot summary in Command Center.

### Safety
- Snapshot management is context only; it does not mutate Operational Truth.

## [0.9.5.70] - Historical Import Integrity & Coverage Drilldown

### Added
- Historical import dashboard service and web panels.
- Missing-data drilldown with historical coverage context.

### Changed
- Historical data is visible as reference coverage, not operational truth.

## [0.9.5.69] - Historical Import Performance Fix

### Changed
- Historical Excel import performance improved to seconds for the provided two-workbook baseline.
- Added progress output and safer report generation.

## Previous changes

See `docs/RELEASE_NOTES.md` and `docs/PATCH_SUMMARY.md` for consolidated sprint history.

## v0.9.5.113 - Gold Blocker Triage

- Adds a diagnostic Gold Blocker Triage report to the Ground Truth Validator.
- Classifies remaining Gold Fidelity blockers by domain: player name, alliance tag, combined identity, rank/power, alignment, and nonlocal/multilingual drift.
- Adds `gold_blocker_triage_summary` and `gold_blocker_triage` to JSON output plus Excel sheets `gold_blocker_triage` and `gold_blocker_details`.
- Keeps matching, inference, Character ReOCR voting, DataGuard, and Operational Truth unchanged. This sprint is diagnostic, not corrective.


## v0.9.5.115 - Latin Player Name Core Resolution

- Extends the local glyph gate to handle Latin-only missing glyphs in otherwise aligned names.
- Adds safe handling for Latin spacing gaps so formatting does not block Core Identity when the compact Latin name is still locally aligned.
- Keeps mixed CJK/Hangul/Kana display drift conservative; no historical identity database or manual mapping is introduced.
- Adds smoke tests for `Mizzenmast -> Mzzenmast`, Latin spacing gaps, and mixed Unicode rejection.

## v0.9.5.114 - Player Name Drift Triage and Core Identity Gold Gate

- Added a transfer-critical Core Identity gate alongside the stricter full row Gold Fidelity gate. Core Identity means verified player display + verified alliance display + matched power/server; rank display drift is now visible as a separate full-fidelity blocker instead of being mixed with name/tag identity failures.
- Added `verified_core_identity_match`, `verified_core_identity_resolution`, `gold_core_blocker`, `verified_core_identity_matches`, `gold_core_blocker_rows`, and `gold_core_ready` to validator/detail summaries.
- Added `core_identity_summary` and `core_identity_verified_rows` to the JSON report, plus `core_identity` and `core_identity_rows` sheets in the Excel report.
- Improved Gold Blocker Triage classes to separate `identity_core_verified_rank_only_blocker`, `identity_core_verified_power_display_blocker`, multilingual/nonlocal player-name drift, and true local glyph failures.
- No Operational Truth write path changed. DataGuard, row-alignment guard, inference read-only handling, and ReOCR voting remain conservative.

Expected effect: `.114` will not magically solve CJK/Hangul player-name drift, but it will stop rank-only/full-row fidelity noise from hiding rows where transfer-critical identity is already proven.
