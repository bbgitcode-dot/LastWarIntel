## [0.9.5.53] - Adaptive Review OCR Pipeline

### Added
- Added adaptive second-pass OCR for ranking rows isolated by review/quarantine.
- Added deterministic row-crop, shifted-crop, 2x zoom, CLAHE, and sharpen variants.
- Added conservative review OCR promotion gate and quarantine fallback.
- Added review OCR metadata to Excel exports and import reports.
- Added smoke tests for variant generation, clear promotion, and report aggregation.

### Changed
- `main.py` now runs review OCR after Ranking/Power Guard and before content reconciliation.
- Player ranking legacy rows now preserve `visual_y` for row-local crop recovery.

### Guardrail
- Review OCR is source-local and row-local; no filename/order/upload truth is introduced.
- Weak review OCR stays quarantined.

### Version
- Version updated to `0.9.5.53`.

# Changelog

All notable changes to Sentinel are documented here. Detailed release notes are consolidated in `docs/RELEASE_NOTES.md`.

---

## [0.9.5.52] - Segment Order Recovery Guardrails

### Added
- Segment-order tie-breaker for close high-explosion THP candidate scores.
- Conservative low-truncation ambiguity gate for `scale_x10` vs `insert_zero` candidate ties.
- Regression coverage for Server 553 segment-order recovery and low-truncation quarantine behavior.

### Changed
- Recovery decision version updated to `v0.9.5.52`.
- Low-truncation recovery now prefers quarantine over false confidence when digit evidence and segment order conflict.
- Version updated to `0.9.5.52`.

## [0.9.5.51] - Digit-Preserving Power Recovery

### Added

- Digit-preservation scoring for low/truncated THP recovery candidates.
- Candidate metadata field `digit_preservation_score`.
- Candidate reason traces for digit-preservation decisions.

### Changed

- Low THP recovery now prefers candidates that preserve visible OCR digit evidence when context margins are narrow.
- Recovery decision version updated to `v0.9.5.51`.
- Version updated to `0.9.5.51`.

---

## [0.9.5.50] - Bidirectional Power Error Model

### Added

- Source-local low/truncated THP recovery candidates.
- OCR error probability scoring for high and low THP power errors.
- Regression coverage for Server 549–553 power error classes.

### Changed

- Candidate scoring now includes OCR error model reasons while retaining margin-gated recovery.
- Version updated to `0.9.5.50`.

---

## [0.9.5.49] - Candidate Decision Engine Cutover

### Changed

- Removed the legacy leading-digit recovery decision path from Ranking Power Sanity Guard.
- Power recovery now selects candidates only through context candidate scoring and explicit score-margin rules.
- Ambiguous candidate ties are quarantined instead of recovered.
- Added decision metadata: `power_recovery_decision_strategy`, `power_recovery_decision_version`, and `power_recovery_legacy_used`.

### Fixed

- Prevented `legacy_leading_digit_recovery` from overriding better-scored or tied candidates.
- Ensured candidate traces identify whether the new decision engine or legacy logic made the call.

---

## [0.9.5.48] - Source Context Recovery Reportability

### Added

- Excel export columns for power candidate recovery metadata.
- Import-report `power_recovery` candidate traces with selected, best, second, margin, confidence, and reason fields.
- Per-import recovery counters for recovered and ambiguous candidate rows.

### Fixed

- Global import-report `review_count` aggregation now matches import-level review warnings.

### Changed

- Version updated to `0.9.5.48`.

---

## [0.9.5.47] - Context-aware Power Candidate Recovery

### Added

- Candidate generation and scoring for suspicious THP and Alliance Power OCR explosions.
- Recovery candidate metadata on recovered and ambiguous rows.
- Regression tests for Server 553-style candidate recovery, including `764M -> 224M` context selection.

### Changed

- Replaced single-path power recovery with context-aware candidate scoring while preserving legacy deterministic safeguards.
- Version updated to `0.9.5.47`.

---

## [0.9.5.46] - Documentation Consolidation

### Added

- `docs/START_NEXT_CHAT.md` for clean project handoff.
- `docs/LESSONS_LEARNED.md` for sprint knowledge retention.
- `docs/ARCHITECTURAL_DECISIONS.md` for ADR-style architecture memory.

### Changed

- Updated project documentation to reflect the actual v0.9.5.45 runtime baseline.
- Updated `PROJECT_STATUS.md` with recent Data Guard, Ranking Guard, Power Sanity, and Server 549–553 findings.
- Updated `ROAD_TO_V1.md` with milestones from Data Integrity Fortress to v1.0.0.
- Updated architecture and operating model documentation.
- Version updated to `0.9.5.46`.

---

## [0.9.5.45] - Source-local Power Digit Recovery

### Added

- Leading digit recovery for suspicious THP and Alliance Power values.
- Recovery metadata for corrected power fields.

### Finding

- Recovery can reduce false `7xxM` and `77B` values, but candidate choice remains heuristic.
- Next sprint should implement context-aware power candidate scoring.

---

## [0.9.5.44] - Source-local Power Sanity Guard

### Added

- Source-local power sanity checks for Ranking Guard.

### Finding

- Guard correctly catches false high values but can increase quarantine noise.

---

## [0.9.5.43] - THP Source-shape Digit Explosion Guard

### Added

- Guard against `164M -> 764M` style OCR explosions.

---

## [0.9.5.42] - Rank / Power Envelope Guard

### Added

- Envelope checks for THP and Alliance Power ranking rows.

---

## Earlier history

Earlier v0.9.5.x releases focused on OCR provider architecture, EasyOCR/PaddleOCR benchmarking, ground truth validation, row alignment, power-first ranking reconstruction, Data Guard, Data Quality Loop, Ranking Guard, and Command Center foundations.

Full historical notes are consolidated in `docs/RELEASE_NOTES.md`.

