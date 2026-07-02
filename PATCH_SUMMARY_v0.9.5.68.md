# Sentinel v0.9.5.68 Patch Summary

## Historical Dataset Import & Coverage Baseline

This patch adds a dedicated historical Excel importer and connects historical SQLite coverage to the Command Center Operational Readiness model.

### Highlights
- Added `importer/historical_excel_import.py`.
- Supports historical workbooks in `/input`:
  - `LastWarS5_post_Transfer.xlsx`
  - `LastWarS6_pre-season.xlsx`
- Generates `data/historical_import_report.json` when run.
- Imports historical rankings into SQLite `historical_*` collections.
- Command Center readiness can include historical server/ranking coverage.
- Added smoke tests for historical import and readiness coverage.

### Guardrails
- Historical data is reference data only.
- Current-run pending reviews still block Operational Truth.
- Benchmark/Ground Truth remains separate from operational coverage.

### Validation
```text
5 passed
compileall importer/historical_excel_import.py application/command_center/service.py web/templates/command_center.html version.py passed
```
