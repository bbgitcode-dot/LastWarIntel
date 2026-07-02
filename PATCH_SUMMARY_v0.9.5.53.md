# Sentinel v0.9.5.53 Patch Summary

## Title
Adaptive Review OCR Pipeline

## Purpose
v0.9.5.52 stabilized power recovery and segment-order guardrails, but the remaining 549–553 review rows showed that many failures are crop/image/row-OCR quality issues rather than additional power-scoring problems. v0.9.5.53 turns review into a controlled second-pass OCR stage.

## Changes
- Added `parser/review_ocr.py`.
- Added adaptive row-local Review OCR after Ranking/Power Guard and before final reconciliation.
- Preserved `visual_y` in player ranking legacy rows so questionable rows can be cropped from the source screenshot.
- Added deterministic review variants: row crop, tall/shifted crops, 2x zoom, CLAHE, and sharpen.
- Added conservative promotion gate: weak or ambiguous review OCR remains quarantine.
- Added `review_ocr_*` metadata to Excel exports and import reports.
- Added top-level `review_ocr` summary to `data/latest_import_report.json`.
- Updated `/docs`, including `LESSONS_LEARNED.md`.
- Added regression tests for adaptive review OCR.

## Validation
```text
pytest tests/smoke/test_adaptive_review_ocr.py tests/smoke/test_operational_import_repository.py tests/smoke/test_ranking_power_sanity_guard.py -q
23 passed

python -m compileall -q parser services models main.py
passed
```

Note: full-repository compile still hits pre-existing invalid legacy files (`analysis/alliance.py`, `analytics/services/ranking_service.py`, old smoke command stubs). These are unchanged by this patch.

## Commit
```bash
git add .
git commit -m "feat(review): add adaptive review OCR pipeline"
git tag -a v0.9.5.53 -m "v0.9.5.53 Adaptive Review OCR Pipeline"
```
