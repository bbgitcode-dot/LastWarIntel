# Sentinel Project Status

**Current version:** v0.9.5.72  
**Current sprint:** Documentation Consolidation & Project Handover  
**Baseline code:** v0.9.5.71  
**Primary focus:** Data integrity before intelligence

## Current Philosophy

**Data Quality comes before Intelligence.**

Sentinel is not just an OCR project. OCR is one sensor in a broader explainable strategic intelligence platform for Last War. The current objective is to make screenshot-derived data reliable, auditable and safe before building deeper assessment and recommendation logic.

The guiding rule remains:

> Quarantine is preferred over false Operational Truth.

Operational Truth may only emerge through guarded validation, Data Guard, Ranking Guard, explicit recovery evidence and Human Review. A dashboard, import script or reviewer click must not silently rewrite truth.

## Current system state

### Stable / usable foundations

- Local screenshot OCR pipeline and parser.
- Ranking extraction for `alliance_power` and `total_hero_power`.
- Data Guard protection for server assignment and runtime truth.
- Ranking Guard for ranking-type contamination and power sanity issues.
- Context-aware power candidate recovery with candidate metadata.
- Review OCR and row reconstruction as conservative remediation stages.
- Persistent Review History (`data/review_history.json`).
- Web Review Center with detail view, screenshot preview, screenshot link and calibrated rank highlight overlay.
- Command Center with Operational Readiness, drilldowns, Imports, Quality and Review navigation.
- Historical Excel importer with fast bulk import and report output.
- Historical coverage baseline from `input/LastWarS5_post_Transfer.xlsx` and `input/LastWarS6_pre-season.xlsx`.
- Managed Snapshot foundation with JSON-backed active snapshot context.

### Current data-source separation

Sentinel must keep these contexts separate:

| Context | Purpose | Truth status |
| --- | --- | --- |
| Current Run | Latest screenshot OCR/import report | Candidate operational evidence |
| Review History | Human-in-the-loop open/resolved review state | Audit/workflow state |
| Historical Dataset | Imported Excel baseline and historical coverage | Reference data |
| Benchmark/Ground Truth | Test and validation data | Development-only validation |
| Operational Truth | Data safe enough for strategic use | Guarded output only |

Server 551 benchmark data must not appear as current-run quality unless it is actually part of the active run or historical dataset view. Historical records may appear under historical coverage, not as live operational completeness.

## Recent sprint achievements

### v0.9.5.47–v0.9.5.54 – Data Integrity Fortress
- Added context-aware power candidate recovery.
- Reduced false OCR digit explosions by scoring candidates against local ranking context.
- Added recovery metadata to reports and exports.
- Added bounded row reconstruction for missing/truncated rows.
- Reinforced the rule that ambiguous cases must remain in quarantine.

### v0.9.5.55–v0.9.5.61 – Review System Foundation
- Added Command Center and Review Dashboard.
- Added Review Evidence Pack.
- Added human-readable review problem statements, choices and explainability traces.
- Added persistent review history and resolution-state foundation.
- Clarified that review resolution is audit evidence, not an immediate export override.

### v0.9.5.62–v0.9.5.65 – Review UX and Evidence Detail
- Consolidated visible navigation.
- Added screenshot links in review detail.
- Added screenshot preview and rank highlight overlay.
- Calibrated overlay so the marked rank aligns with the visible row.

### v0.9.5.66–v0.9.5.70 – Operational Readiness and Historical Coverage
- Added Operational Readiness tiles and drilldowns.
- Corrected current-run vs historical vs benchmark separation.
- Added fast historical Excel import.
- Added historical import report and coverage drilldown.

### v0.9.5.71 – Snapshot Management Foundation
- Added JSON-backed managed snapshots.
- Added active snapshot display in Command Center and Import Center.
- Introduced Snapshot as the planned container for future screenshot uploads.

## Immediate next steps

### Next development focus: Snapshot workflow hardening

The snapshot concept exists, but it must become the default import context.

Required next work:

1. Make **Create Snapshot** visible and natural in Import Center.
2. Require or prompt for an active snapshot before screenshot upload/import.
3. Bind `latest_import_report.json`, review history entries and generated exports to the active snapshot.
4. Show snapshot-level coverage: expected servers, received servers, missing ranking feeds and open reviews.
5. Prevent accidental mixing of screenshots from different events/phases.

Example target snapshot:

```text
Snapshot: S6 pre Transfer
Type: screenshot_upload
Expected feeds: alliance_power, total_hero_power
Status: open/importing/review/complete
```

### Following focus: Upload/OCR integrity last-mile improvements

After snapshot workflow is explicit, return to data-integrity improvements:

- image upload preflight checks,
- screenshot quality scoring,
- duplicate screenshot detection,
- row geometry confidence,
- source-local completeness checks,
- review crop/line evidence where needed,
- clearer missing-data causes.

## Known risks and limitations

- Snapshot binding is foundational but not yet fully enforced across all import artifacts.
- Review resolution is stored as workflow evidence; guarded override into exports still needs a separate Manual Override Engine.
- Historical data is imported and visible but must remain reference coverage until explicitly promoted by future guarded workflows.
- ADR files currently contain duplicate numbers from earlier sprint history. The canonical architectural decisions are summarized in `docs/ARCHITECTURAL_DECISIONS.md`; ADR numbering should be cleaned in a later documentation/refactoring sprint.
- Static output artifacts still exist alongside web pages. The long-term goal is a single navigable web flow.

## Definition of done for the current phase

The current Data Integrity phase is complete when:

- every screenshot import belongs to an explicit snapshot,
- current run, historical data and benchmark data cannot be confused,
- all suspicious power/name/rank/server cases are either recovered with strong evidence or quarantined,
- review items are explainable and actionable,
- unresolved reviews block Operational Truth instead of silently exporting questionable data,
- the Command Center answers: what exists, what is complete, what is missing and what needs human action.
