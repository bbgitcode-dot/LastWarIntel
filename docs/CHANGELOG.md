## [0.9.5.61] - Interactive Review Resolution Foundation

### Added
- Added first web Review Center resolution actions for persistent review-history items.
- Added candidate selection, manual value, manual name, manual alliance, reviewer, and comment capture.
- Added reopen action for resolved review records.
- Added smoke coverage for resolving and reopening review-history records.

### Changed
- Review Center now separates open and resolved review work.
- Static Review Center copy clarifies that static pages remain read-only while `/reviews` handles resolution state.
- Version updated to `0.9.5.61`.

### Safety
- Review resolution does not change Operational Truth, OCR evidence, quarantine, or Excel export rows.
- Resolution data remains an auditable human decision record until a future guarded override engine consumes it.

## [0.9.5.59] - Review UX & Explainability Foundation

### Added
- Added integrated `review_center.html` as the human-in-the-loop review workspace.
- Added explainability notes (`why_bullets`) and decision path traces (`explainability_steps`) for review evidence.
- Added persistent review-history visualization with OPEN/RESOLVED status foundation.
- Added resolution template fields for future browser-based review completion.

### Changed
- Command Center now links to the Review Center as the preferred review path.
- Review Evidence Pack remains available as a legacy evidence detail page.

### Safety
- No OCR, Data Guard, Ranking Guard, or Operational Truth promotion logic changed.
- Review UI remains read-only.

## [0.9.5.58] - Human Review Guidance

### Added
- Review Evidence Pack now states the human-facing problem explicitly for each review item.
- Evidence choices list Vorschlag 1/2/3 plus manual input as the next decision options.
- Persistent `data/review_history.json` foundation for historical open/resolved review tracking.

### Changed
- Review cards now separate problem, decision needed, candidate choices, and raw trace details.
- Version updated to `0.9.5.58`.

## [0.9.5.57] - Evidence Trace Binding

### Added

- Review Evidence Pack now binds review rows to matching `power_recovery.traces` even when the trace was emitted under `ranking_guard_quarantine` rather than the expected ranking type.
- Evidence cards now expose trace status, source file, candidate count, digit-preservation score, best/second candidate, margin, and candidate reasons where available.
- Command Center and Review Dashboard review rows now link directly into the matching evidence card (`review_evidence_pack.html#REV-xxx`).
- Smoke coverage for quarantine-trace binding by screenshot and ambiguous margin hints.

### Changed

- Evidence matching now uses exact keys first, then conservative screenshot-local fallback with rank, ranking type, best-score, and margin hints.
- Version updated to `0.9.5.57`.

### Guardrail

- Trace binding is visualization only. It does not promote rows, alter export data, or resolve review items.

## [0.9.5.56] - Review Evidence Pack

### Added

- Static `output/review_evidence_pack.html` focused on review-item evidence rather than broad dashboard telemetry.
- Machine-readable `output/review_evidence_pack.json` with one evidence object per review item.
- Evidence cards with location, screenshot reference, power original/selected, best/second candidate, margin, decision reason, suggested action, and candidate details.
- Command Center links to the Evidence Pack.
- Smoke coverage for evidence pack generation.

### Changed

- `main.py` now prints the generated Review Evidence Pack path after each run.
- Version updated to `0.9.5.56`.

### Guardrail

- Evidence Pack is read-only. It does not promote rows, alter exports, or override Data Guard / Ranking Guard decisions.


## [0.9.5.55] - Command Center MVP

### Added

- Static Sentinel Command Center generated after each import run.
- Static Review Dashboard generated after each import run.
- Report-driven HTML renderer in `services.command_center`.
- Smoke coverage for dashboard generation from import, ground-truth, and inference reports.

### Changed

- `main.py` now writes `output/command_center.html` and `output/review_dashboard.html` after `data/latest_import_report.json`.
- Version updated to `0.9.5.55`.

### Guardrail

- Command Center reads reports only; it does not duplicate OCR, recovery, Data Guard, or quarantine logic.


## [0.9.5.54] - Contextual Row Reconstruction

### Added

- Conservative source-local row reconstruction for review/quarantine THP rows.
- Anchor-based bounded-gap promotion after Adaptive Review OCR.
- Row reconstruction metadata in Excel export and import report.

### Finding

- The remaining 549–553 hard cases are often bounded row/rank reconstruction problems, not simple OCR enhancement problems.

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

## v0.9.5.60 - Command Center Consolidation

- Added stable review-history identity keys so reruns update open reviews instead of duplicating them.
- Added `/reviews` as the consolidated web Review Center entry point.
- Mounted latest static output reports under `/static-output` for transitional run-detail access.
- Updated navigation taxonomy around Command Center, Imports, Quality, Reviews, Operations, and Intelligence.
- Kept OCR, Data Guard, Ranking Guard, and recovery logic unchanged.

## v0.9.5.62 - Visible Navigation Consolidation

- Added a persistent Command Center workflow bar across the web UI: Command, Imports, Quality, Reviews, Exports.
- Expanded the sidebar from icon-only navigation to readable grouped navigation with labels and descriptions.
- Added Review Detail pages under `/reviews/{history_key}` so review evidence can be reached from the web app instead of only from static output HTML.
- Added page-to-page cross-links between Command Center, Imports, Quality, Reviews, Exports, and latest static run reports.
- Added shared CSS for workflow cards, review evidence details, resolution forms, and responsive layout.
- Added smoke coverage for visible navigation and Review Detail routing.
- Updated version to `0.9.5.62`.

No OCR, Data Guard, Ranking Guard, recovery, or export logic changed.

## v0.9.5.63 - Human Review Screenshot Evidence

- Added clickable source-screenshot links to Review Detail and Review Queue.
- Added Review Detail screenshot preview that opens the original screenshot in a new tab.
- Mounted `/screenshots` in the FastAPI web app for source evidence access.
- Hardened screenshot URL generation by using screenshot basenames only.
- Updated CSS so screenshot evidence panels match the consolidated Command Center design.
- Updated version to `0.9.5.63`.

## v0.9.5.64 - Review Evidence Highlight Overlay

- Reworked Review Detail into a two-column human-review workspace.
- Added compact screenshot evidence preview so the screenshot no longer overwhelms the decision workflow.
- Added target rank highlight overlay and badge based on review `ranking_type` and `rank`.
- Kept full-resolution screenshot links opening in a new tab.
- Added `/docs/PATCH_SUMMARY.md` as the consolidated patch-summary document.
- Updated smoke tests and version to `0.9.5.64`.

No OCR, Data Guard, Ranking Guard, recovery, or export logic changed.
