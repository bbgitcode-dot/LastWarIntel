# Changelog

## [0.9.5.29] - Ranking Guard Recovery

### Added

- Evidence-based Ranking Guard Recovery layer.
- Recovery metrics in operational import reports.
- Smoke tests for safe recovery and calibration decisions.

### Changed

- Ranking Guard can now recover provably safe ranking-type assignments before quarantine.
- False-positive alliance-name shapes can be calibrated without being quarantined.
- Version updated to `0.9.5.29`.



## [0.9.5.27] - Recoverable Gap Intelligence

### Added

- Evidence Resolver for Ground Truth validation gaps.
- Unique exact-power recovery and conservative near-power recovery.
- Smoke tests for evidence recovery and validator integration.

### Changed

- Ground Truth Validator now reports recoverable inferred matches as explicit `gap_*` methods.
- Version updated to `0.9.5.27`.

All notable changes to Sentinel are documented here.

This file summarizes major release milestones. Detailed historical notes are consolidated in `docs/RELEASE_NOTES.md`.

---

## [0.9.5.26] - Ground Truth Validation Framework

### Added

- Operational Ground Truth validation defaults for Server 551 Top 50 THP and current export.
- Server-scoped precision metrics for multi-server exports.
- Ranking Guard quarantine evidence in Ground Truth validation reports.
- Failure classification and failure summary for validation details.

### Changed

- Version updated to `0.9.5.26`.

---

## [0.9.5.25] - Sentinel Ranking Guard

### Added

- `parser/ranking_guard.py` as a modular Data Guard integrity component for ranking-type validation.
- Runtime quarantine path `REVIEW_ranking_guard_quarantine`.
- Import report and Command Center review metadata for ranking-type conflicts.
- Smoke tests for THP-in-Alliance-Power and Alliance-Power-in-THP contamination.
- `docs/SENTINEL_DATA_GUARD.md` to preserve the Data Guard doctrine as the central integrity model.

### Changed

- Import pipeline now applies Ranking Guard before content reconciliation and export.
- Operational import report now lists `ranking_guard` as an integrity check.
- Version updated to `0.9.5.25`.


## [0.9.5.28] - Inference Engine Core

### Added

- Read-only `inference/` package.
- Context Engine for explainable bounded-gap inference.
- Inference JSON/XLSX reports.

### Changed

- Ground Truth validation can mark accepted contextual inferences separately from observed OCR matches.
- Version updated to `0.9.5.28`.

## [0.9.5.24] - Documentation Consolidation

### Added

- `docs/ROAD_TO_V1.md`.
- `docs/MODUS_OPERANDI.md`.
- Updated documentation for Command Center, Sentinel Data Guard, Sentinel Data Quality Loop, quarantine, and upcoming Ranking Guard.

### Changed

- Consolidated scattered release-note files into `docs/RELEASE_NOTES.md`.
- Updated `PROJECT_STATUS.md`, `ROADMAP.md`, `ARCHITECTURE.md`, `README.md`, `SENTINEL.md`, `VISION.md`, and `INTELLIGENCE.md` to reflect the current operational platform state.
- Version updated to `0.9.5.24`.

---

## [0.9.5.23] - Sentinel Data Quality Loop

### Added

- Quality Loop for targeted OCR recovery.
- Safe Data Guard quarantine for suspicious blocks.
- Recovery attempt metadata.

### Changed

- Suspicious server blocks are quarantined instead of silently merged.
- Filename and timestamp logic are excluded from server assignment decisions.

---

## [0.9.5.22] - Data Guard Hotfix Attempt

### Added

- Content-first Data Guard server reconciliation.

### Finding

- Hotfix removed false 552 output but risked overcorrection by merging suspicious rows into 551.
- This led to the quarantine doctrine implemented in v0.9.5.23.

---

## [0.9.5.21] - Sentinel Data Guard

### Added

- Sentinel Data Guard Phase 1.
- Operational import report.
- Command Center live import state.

---

## [0.9.5.20] - Architecture Consolidation

### Changed

- Ground Truth removed from runtime dependency path.
- Command Center reads through repository/service boundary.

---

## [0.9.5.19] - Command Center Foundation

### Added

- FastAPI application shell.
- Command Center UI.
- Imports and Quality views.
- Health/status/version endpoints.

---

## [0.9.5.18] - Parser Stabilization

### Added

- Ground Truth validation improvements.
- Ranking alignment and gap handling.
- Parser quality metrics.

---

## Earlier history

Earlier v0.9.5.x releases focused on OCR provider architecture, EasyOCR/PaddleOCR benchmarking, ground truth validation, duplicate column fixes, row alignment, parser normalization, and quality metrics.

Full historical notes are available in `docs/RELEASE_NOTES.md`.
