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
