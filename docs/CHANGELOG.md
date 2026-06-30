# Changelog

All notable changes to Sentinel are documented here.

This file summarizes major release milestones. Detailed historical notes are consolidated in `docs/RELEASE_NOTES.md`.

---

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
