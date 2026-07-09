# RELEASE_NOTED.md

Canonical release notes live in `RELEASE_NOTES.md`. This file exists only as a compatibility pointer because the handover request mentioned `RELEASE_NOTED.md`.


## v0.9.5.130
- Strategic focus shifted from OCR accuracy to Display Reconstruction Engine.
- Documented next milestone around verified_display_name / verified_display_alliance_tag.
- Updated roadmap based on latest validation reports.


## v0.9.5.131 – Display Reconstruction Engine Phase I

- Added a read-only Display Reconstruction Engine inside `ground_truth_validator.py`.
- New report outputs:
  - `display_reconstruction_report.json`
  - `display_reconstruction_report.xlsx`
  - `display_reconstruct` and `display_recon_rows` sheets in the main validation workbook.
- The engine consumes existing Character ReOCR evidence and read-only contextual inference evidence to produce report-only fields:
  - `display_reconstructed_name`
  - `display_reconstructed_alliance_tag`
  - `display_reconstruction_status`
  - `display_reconstruction_source`
  - `display_reconstruction_confidence`
  - `display_reconstruction_operational_truth_modified`
- Guardrail: no Ground Truth, OCR export, snapshot, verified display field, or Operational Truth field is modified.
- Added smoke tests for local character reconstruction, context-gap display suggestions, and report generation.

Strategic intent: Sentinel now starts converting stored character evidence into explainable display proposals without weakening DataGuard.

## v0.9.5.132 – Display Reconstruction Guard

- Added guarded promotion rules for report-only display reconstruction.
- Blocks unsafe name promotion from `UNKNOWN`, low coverage, unresolved fragments, or observed-vote conflicts.
- Added `display_promotion_eligible` and `display_promotion_block_reason`.
- Operational Truth remains unchanged.

## v0.9.5.133 – Evidence Confidence Engine

- Added read-only `evidence_confidence_report.json/xlsx`.
- Added fragment confidence components for crop, OCR, votes, position, unicode/script and status.
- Added display coverage metrics for name/tag/display proposals.
- Added `display_confidence_decision`.
- DataGuard remains unchanged; Operational Truth is not modified.


## v0.9.5.134 – Evidence Budget Manager

- Added `evidence_budget_report.json` and `evidence_budget_report.xlsx`.
- Added read-only fields: `evidence_priority_score`, `evidence_budget_tier`, `evidence_budget_action`, `evidence_budget_reason`.
- Added budget recommendation layer for future Character ReOCR runtime reduction.
- Operational Truth remains unchanged.


## v0.9.5.135 – Evidence Scheduler Phase I

- Added read-only Evidence Scheduler reports and queue decisions.
- Converts passive Evidence Budget recommendations into an execution plan.
- No Operational Truth mutation.

## v0.9.5.136 – Gold Accuracy Mode

Functional accuracy sprint. Sentinel now treats runtime as secondary during Gold Fidelity work. `GOLD_ACCURACY_MODE` is enabled in the validator, local glyph ReOCR budget skips are disabled, and Evidence Scheduler decisions no longer early-exit rows solely to save runtime. Context-gap evidence remains read-only and Operational Truth remains locked.

