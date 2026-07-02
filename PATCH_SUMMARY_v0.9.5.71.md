# Sentinel v0.9.5.71 Patch Summary

## Release

v0.9.5.71 – Snapshot Management Foundation

## Focus

Introduce explicit managed snapshot context for screenshot upload batches, so future imports can be tied to a human-named phase such as `S6 pre Transfer` instead of being interpreted only as "latest run".

## Key changes

- Added `application.snapshots` with a JSON-backed `SnapshotService` and view models.
- Added persistent `data/managed_snapshots.json` storage for active/open/complete managed snapshots.
- Added Import Center snapshot creation form with expected core feeds (`alliance_power`, `total_hero_power`).
- Added snapshot activation and status-update routes.
- Added active snapshot summary to the Command Center when a snapshot is selected.
- Kept snapshot management separate from Operational Truth, SQLite historical records, OCR decisions, and exports.
- Updated version and documentation to v0.9.5.71.

## Validation

```text
pytest tests/smoke/test_snapshot_management.py tests/smoke/test_historical_excel_import.py -q
4 passed
python -m compileall -q application/snapshots application/command_center web/routes web/templates version.py
```

## Commit

```bash
git add .
git commit -m "feat(import): add managed snapshot context"
git tag -a v0.9.5.71 -m "v0.9.5.71 Snapshot Management Foundation"
```
