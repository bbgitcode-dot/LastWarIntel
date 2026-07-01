# Sentinel v0.9.5.48 Patch Summary

## Release

v0.9.5.48 – Source Context Recovery Reportability

## Focus

Expose context-aware power candidate scoring in operational outputs and fix import-report review-count aggregation.

## Key changes

- Added power candidate recovery metadata columns to Excel exports.
- Added top-level `power_recovery` candidate traces to `data/latest_import_report.json`.
- Added per-import recovery counters.
- Added direct row metadata for best candidate, second candidate, margin, status, confidence, and reason.
- Fixed global `review_count` aggregation so it no longer reports zero while import blocks report review warnings.
- Updated documentation and version to v0.9.5.48.

## Validation

```bash
python -m compileall -q parser services main.py version.py
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_operational_import_repository.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_ranking_recovery.py -q
```

Observed:

```text
23 passed
```

## Commit

```bash
git add .
git commit -m "feat(reporting): expose power candidate recovery traces"
git tag -a v0.9.5.48 -m "v0.9.5.48 Source Context Recovery Reportability"
```
