# Sentinel Patch Summary

**Current release:** v0.9.5.72 – Documentation Consolidation & Project Handover  
**Updated:** 2026-07-02

This is the canonical patch-summary document. Future sprint patches should update this file instead of creating loose `PATCH_SUMMARY_v*.md` files, unless a temporary root-level file is needed inside a delivered patch package.

## v0.9.5.72 – Documentation Consolidation & Project Handover

### Purpose
Consolidate Sentinel project knowledge after the v0.9.5.47–v0.9.5.71 sprint sequence. This sprint locks down the current architecture, operating rules, known risks and next milestones before the next development chat.

### Included changes
- Updated `/docs/RELEASE_NOTES.md` as the canonical release-note ledger.
- Updated `/docs/PATCH_SUMMARY.md` as the canonical patch-summary ledger.
- Updated `/docs/PROJECT_STATUS.md` with current project state and immediate next steps.
- Updated `/docs/ROAD_TO_V1.md` with milestones through v1.0.0.
- Updated `/docs/MODUS_OPERANDI.md` with Proud Owner/Mimir sprint rules.
- Updated `/docs/ARCHITECTURAL_DECISIONS.md` with current guardrails and future decisions.
- Updated `/docs/LESSONS_LEARNED.md` with lessons from review, historical import, coverage and snapshot work.
- Added `/docs/NEXT_CHAT.md` for clean handoff.

### Validation
```text
Documentation files generated and reviewed.
Version set to 0.9.5.72.
No runtime behavior changes intended.
```

### Commit
```bash
git add .
git commit -m "docs(project): consolidate Sentinel handoff documentation for v0.9.5.72"
git tag -a v0.9.5.72 -m "v0.9.5.72 Documentation Consolidation and Project Handover"
```

## Consolidated patch-history sources

---

## Source: `PATCH_SUMMARY_v0.9.5.70.md`

# Sentinel v0.9.5.70 Patch Summary

## Historical Import Integrity & Coverage Drilldown

This patch makes historical Excel coverage visible and auditable from the web UI after the v0.9.5.69 importer performance fix.

### Included changes
- New read-only `application.historical_import` dashboard service.
- Import Center panels for historical Excel report, source collections and SQLite snapshot coverage.
- Quality missing-data drilldown now displays operational missing evidence plus historical baseline context.
- Historical data remains reference coverage and does not overwrite Operational Truth.
- Updated `/docs/PATCH_SUMMARY.md`, release notes, changelog, lessons learned and project status.

### Validation
```text
7 passed
compileall application/historical_import importer/historical_excel_import.py application/command_center/service.py web/routes web/templates version.py passed
```

### Commit
```bash
git add .
git commit -m "feat(import): expose historical coverage drilldown"
git tag -a v0.9.5.70 -m "v0.9.5.70 Historical Import Integrity and Coverage Drilldown"
```

---

## Source: `PATCH_SUMMARY_v0.9.5.71.md`

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

