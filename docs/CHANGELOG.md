# Changelog

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
