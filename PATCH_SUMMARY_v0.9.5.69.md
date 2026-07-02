## v0.9.5.69 - Historical Import Performance Fix

Focus: make historical Excel import fast, observable, and safe for the S5/S6 baseline workbooks.

### Fixed
- Replaced per-row SQLite writes with cached bulk writes inside a sheet-level transaction.
- Added `--verbose` progress output for file/sheet-level import visibility.
- Removed the slow computed-rank monkey-patch flow and computes ranks directly in memory.
- Writes a partial import report even when an import is interrupted or fails.

### Improved
- Caches collections, ranking types, snapshots, and entities during import.
- Limits processing to the explicitly supported historical workbook sheets.
- Reports per-collection duration, status, imported rows, skipped rows, and covered servers.
- Keeps historical imports as reference data only; no Operational Truth, latest OCR report, review history, or export behavior is changed.

### Validation
```text
2 passed tests/smoke/test_historical_excel_import.py
Actual workbook import: 3024 rows, 128 servers, importer duration 1.16s
compileall importer/historical_excel_import.py version.py passed
```

### Command
```bash
python importer/historical_excel_import.py --input-dir input --report data/historical_import_report.json --verbose
```

### Commit
```bash
git add .
git commit -m "fix(import): speed up historical excel import"
git tag -a v0.9.5.69 -m "v0.9.5.69 Historical Import Performance Fix"
```
