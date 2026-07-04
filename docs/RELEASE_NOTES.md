## v0.9.5.89 – Non-cache Data Quality Validation & Rank Slot Regression

Purpose: continue the truth-first data-quality sprint line by making pending rank slots and raw observed identity visible in exports and covered by regression tests.

### Changed

- Added `tests/smoke/test_data_quality_89.py`.
- Added regression coverage for development cache-off defaults, quarantined rank-slot preservation, `Sven the vän` / `[SWSq]` display fidelity and pending-slot Excel export visibility.
- Extended Excel export preferred columns with pending-review state and observed/normalized/canonical identity fields.
- Bumped `version.py` to `0.9.5.89`.
- Bumped recognition-quality telemetry version to `v0.9.5.89`.
- Updated docs, patch summary, handoff and `.commit`.

### Validation

```text
7 passed  – targeted data-quality tests
27 passed – ranking power sanity + data-quality + recognition-quality targeted suite
compileall OK
full smoke collection blocked by pre-existing legacy invalid/stale smoke tests
zip integrity OK
```

### Git

```bash
git add .
git commit -m "test(data-quality): preserve rank slots and raw identity in exports"
git tag -a v0.9.5.89 -m "v0.9.5.89 Non-cache Data Quality Validation and Rank Slot Regression"
```

---

## v0.9.5.88 – Documentation Consolidation & Handoff Sprint

Purpose: consolidate Sentinel documentation after the v0.9.5.87 data-quality stabilization sprint and prepare a clean handoff for the next chat.

Changed:

- Consolidated the documentation baseline around `/docs` as the canonical documentation path.
- Updated `PROJECT_STATUS.md` with the current recognition-quality state, cache decision, rank-slot preservation goal, and remaining data-stability risks.
- Updated `ROAD_TO_V1.md` with the remaining milestones to v1.0.0.
- Updated `MODUS_OPERANDI.md` to explicitly describe Proud Owner / Mimir roles, full-ZIP sprint delivery, versioning, `.commit`, and no-snippet default delivery.
- Added/updated `NEXT_CHAT.md` and `START_NEXT_CHAT.md` with copy/paste handoff instructions for the next Sentinel chat.
- Added `HANDOFF_NEXT_CHAT.md` as the clean standalone next-chat bootstrap document.
- Updated `SENTINEL_DATA_GUARD.md`, `LESSONS_LEARNED.md`, and `PATCH_SUMMARY.md` with the key lessons from v0.9.5.80–v0.9.5.87.
- Documented that OCR cache is a performance optimization only and must stay disabled in development/data-quality validation until Operational Truth is stable.

Validation:

```text
28 passed
targeted compile OK
zip integrity OK
```

Commit:

```bash
git add .
git commit -m "docs(project): consolidate handoff and road to v1 after data quality stabilization"
git tag -a v0.9.5.88 -m "v0.9.5.88 Documentation Consolidation and Handoff"
```

## v0.9.5.86 – Source Row Identity & Display Fidelity

- Added same-screenshot source-evidence anchoring for Ranking Guard reviews.
- If a quarantined row matches a trusted observed row on the same screenshot by identity/power evidence, the review now uses the observed row rank instead of the quarantine ordinal.
- Preserves raw/observed name and alliance tag fields ahead of normalized fields in review target context.
- Adds recognition telemetry for `source_evidence_anchor_reviews`.
- Keeps OCR Source, Operational Mapping and Operational Truth separated.

Validation:

```text
source-row identity smoke tests passed
targeted compile OK
zip integrity OK
```

Commit:

```bash
git add .
git commit -m "fix(review): anchor source row identity and preserve display fidelity"
git tag -a v0.9.5.86 -m "v0.9.5.86 Source Row Identity and Display Fidelity"
```

## v0.9.5.85 – Recovery Promotion Rules & OCR Cache

- Added a persistent, content-hash based OCR cache for metadata and row OCR observations.
- Added CLI switch `--no-ocr-cache` and environment override `SENTINEL_OCR_CACHE=0`.
- Added telemetry counters for OCR cache hits, misses, writes and errors.
- Added conservative near-miss low-truncation promotion rules for order-consistent THP recoveries.
- Updated recognition quality versioning to v0.9.5.85.
- Added smoke coverage for OCR cache reuse and near-miss recovery promotion.

Validation:

```text
21 passed
targeted compile OK
zip integrity OK
```

## v0.9.5.84 – Power Recovery Diagnostics & Candidate Family Telemetry

- Adds explicit `power_recovery_family` classification for recovered and ambiguous power rows.
- Splits power-recovery telemetry by family so alliance high explosions, THP high explosions, low truncations and generic context candidates are measurable separately.
- Adds `near_miss_ambiguous` counters for close candidate margins that are prime targets for the next recognition-tuning pass.
- Extends Command Center and Evidence Pack power-recovery summaries with near-miss counts and recovery-family labels in trace tables.
- Keeps the .81 Review Evidence Model unchanged: OCR Source, Operational Mapping and Operational Truth remain separate.

Validation:

```text
19 passed (ranking power sanity + recognition quality smoke)
targeted compile OK
zip integrity OK
```

Commit:

```bash
git add .
git commit -m "feat(recognition): classify power recovery families"
git tag -a v0.9.5.84 -m "v0.9.5.84 Power Recovery Diagnostics"
```


## v0.9.5.82 – Recognition Quality Pass

- Adds runtime telemetry to import runs so OCR, parsing, recovery, report rendering and export costs are visible in `data/latest_import_report.json`.
- Adds recognition-quality metrics: auto-accepted rows, power-validated rows, power-outlier quarantines, human review items and power-recovery success rate.
- Adds a conservative guarded promotion path for high alliance-power OCR explosions when candidate evidence is strong, order-consistent and source-local.
- Command Center surfaces Recognition Quality and Runtime / Screenshot metrics for faster quality benchmarking.
- Keeps Continuous Collection behavior from .80: normal imports do not close the snapshot.

Validation:

```text
16 passed
compileall OK
zip integrity OK
```

Commit:

```bash
git add .
git commit -m "feat(data-guard): add recognition quality telemetry"
git tag -a v0.9.5.82 -m "v0.9.5.82 Recognition Quality Pass"
```


## v0.9.5.81 – Review Evidence Model

- Separates Review UI into **OCR Source**, **Operational Mapping**, and pending **Operational Truth**.
- Source-row-only reviews now label the overlay as `OCR Row N` instead of implying a proven rank.
- Review Detail, Review Center, static review reports, and history tables now use `Operational Rank` only when Sentinel has proven one.
- Adds human-facing OCR Source identity fields so reviewers know which player/alliance row the highlight refers to.

Validation:

```text
pytest tests/smoke/test_review_identity_consistency.py tests/smoke/test_review_context.py
compileall OK
zip integrity OK
```

Commit:

```bash
git add .
git commit -m "fix(review): separate OCR source from operational mapping"
git tag -a v0.9.5.81 -m "v0.9.5.81 Review Evidence Model"
```


## v0.9.5.80 – Continuous Collection & Source-Row Review Clarity

- Changed screenshot import lifecycle behavior: normal `python main.py` runs no longer move the active snapshot from `COLLECTING` to `REVIEWING` automatically.
- Added explicit `--finish-collection` flag for operators who intentionally want to close intake after a run and advance the snapshot to `REVIEWING` or `VERIFIED`.
- Hardened Review rendering for `source_row_only` cases: Sentinel now shows `Source Row N · Visible Rank unresolved` instead of falling back to `Rank N` when no global visible rank is proven.
- Evidence Pack and Review Detail now use the same conservative rank context, preventing misleading prompts during manual review.
- Added smoke coverage for source-row-only review rendering.

Validation:
```text
3 passed (review identity smoke)
compileall OK
zip integrity OK
```

Commit:
```bash
git add .
git commit -m "fix(snapshot): keep collecting after imports"
git tag -a v0.9.5.80 -m "v0.9.5.80 Continuous Collection and Source-Row Review Clarity"
```

## v0.9.5.79 – Review Identity Consistency Fix

- Fixed review identity drift where Review cards could show a technical/source row as a visible ranking rank.
- Added conservative `source_row_only` handling: if Sentinel only knows the row inside the screenshot, the UI now says `Source Row` and marks visible rank as unresolved instead of pretending it knows the global rank.
- Review IDs now continue from persistent Review History instead of restarting at `REV-001` on every run. Existing review identities keep their stable REV id; new review identities receive the next number.
- Review Target, Location, Evidence overlay and Review Center list now share the same rank context fields: `visible_rank`, `source_row`, `raw_review_rank`, and `rank_trace_source`.
- Added smoke coverage for source-row-only reviews and monotonic Review IDs.

Validation:

```text
19 passed
compileall OK
zip integrity OK
```

Commit:

```bash
git add .
git commit -m "fix(review): keep review identity and source row consistent"
git tag -a v0.9.5.79 -m "v0.9.5.79 Review Identity Consistency Fix"
```

## v0.9.5.78 – Developer Benchmark & Report Rebuild Mode

Focus: reduce iteration cost for recognition/review quality work so the 99-screenshot production benchmark does not need to be run for every UI or reporting fix.

### Added

- `python main.py --rebuild-reports` to regenerate Command Center, Review Dashboard and Review Evidence Pack from `data/latest_import_report.json` without running OCR.
- Developer screenshot filters for small targeted runs:
  - `--screenshots "Screenshot_20260702-082210.png"`
  - `--screenshots "*082210*.png,*194413*.png"`
  - `--limit N`
- Optional quick-run switches:
  - `--skip-excel`
  - `--skip-command-center`
- Environment fallbacks for local benchmark automation:
  - `SENTINEL_SCREENSHOTS`
  - `SENTINEL_SCREENSHOT_LIMIT`
- Smoke tests for developer run selection and report-rebuild argument parsing.

### Changed

- Default `python main.py` behavior remains unchanged for operational imports.
- Screenshot filters are explicitly treated as developer input selection only; they do not become truth about server, ranking, rank or upload order. Operational truth remains OCR/Data Guard driven.
- Recognition telemetry version advanced to `v0.9.5.78`.

### Validation

```text
python -m compileall -q main.py services web parser application
pytest -q tests/smoke/test_developer_run_modes.py tests/smoke/test_review_rank_trace.py tests/smoke/test_review_context.py tests/smoke/test_command_center.py tests/smoke/test_operational_import_repository.py
# 15 passed
```

### Git

```bash
git add .
git commit -m "chore(dev): add benchmark and report rebuild modes"
git tag -a v0.9.5.78 -m "v0.9.5.78 Developer Benchmark and Report Rebuild Mode"
```

---

## v0.9.5.77 – Review Context & Explainability

- Fixed Review Detail surfaces that exposed internal/quarantine ranks as if they were visible in the linked screenshot.
- Review cards now prefer `visible_rank` and keep `target_rank` / `raw_review_rank` as internal trace fields only.
- Screenshot overlays now position highlights by row inside the screenshot rank window while labelling the human-visible rank. Example: visible rank 66 in window 64-72 highlights row 3 and labels Rank 66.
- Added review target context fields for human validation: target name, alliance/tag, OCR/source power, visible rank, screenshot window and internal target rank.
- Review problem statements now name the affected player/alliance when available, reducing reviewer ambiguity.
- Added smoke coverage for Review Context and overlay row-index calculation.

Validation:

```text
python -m compileall -q services web parser
pytest -q tests/smoke/test_review_rank_trace.py tests/smoke/test_review_context.py tests/smoke/test_command_center.py tests/smoke/test_operational_import_repository.py
# 11 passed
```

# Release Notes

**Current release:** v0.9.5.77 – Review Context & Explainability  

## v0.9.5.76 – Recognition Quality & Data Integrity Pass

Focus: harden screenshot recognition and review explainability based on the first 99-screenshot production-style run.

### Added

- Review Rank Trace: ranking-guard reviews now distinguish the Review ID/raw quarantine row from the actual visible ranking rank in the screenshot.
- Screenshot rank-window awareness: review items can carry `screenshot_rank_window`, `visible_rank`, `raw_review_rank`, and `rank_trace_source`.
- Recognition telemetry in the import report, including source rank-window count, rank-trace fixes, explosive power traces, ambiguous power reviews, and seconds per screenshot.
- Review history current/stale markers plus current/stale open counts to explain differences between current review items and persistent historical open reviews.
- Smoke coverage for screenshot-window rank mapping.

### Fixed

- Misleading review wording such as “Rang 2” or “Rang 3” when the linked screenshot actually shows a later rank window such as 10–18 or 64–72.
- Trace matching now falls back to `raw_review_rank`, so evidence can still bind after the visible rank is corrected for the human review surface.

### Git

```bash
git add .
git commit -m "feat(recognition): add review rank trace and quality telemetry"
git tag -a v0.9.5.76 -m "v0.9.5.76 Recognition Quality and Data Integrity Pass"
```

---

# Release Notes

**Current release:** v0.9.5.75 – Snapshot Lifecycle & Operational Readiness  

## v0.9.5.75 – Snapshot Lifecycle & Operational Readiness

### Added

- Formal snapshot lifecycle: `open`, `collecting`, `reviewing`, `verified`, `locked`, `archived`.
- Status alias migration for older states: `importing → collecting`, `review → reviewing`, `complete → verified`, `closed → locked`.
- Import/edit gates so only safe lifecycle states accept mutation.
- Operational Readiness model for active snapshots.
- Snapshot completion report generation under `reports/snapshots/<snapshot_id>/completion_report.json`.
- Snapshot audit trail for creation, activation, edits, lifecycle transitions and report creation.
- Import Center UI for lifecycle states, readiness, audit and report generation.

### Changed

- Screenshot imports now move snapshots to `collecting` and finish as `reviewing` or `verified`.
- Snapshot-bound import reports use schema `sentinel.import_run.v3`.
- Verified, locked and archived snapshots are read-only.

### Commit

```bash
git add .
git commit -m "feat(snapshot): add lifecycle and operational readiness"
git tag -a v0.9.5.75 -m "v0.9.5.75 Snapshot Lifecycle and Operational Readiness"
```

---

# Sentinel Release Notes

**Current release:** v0.9.5.74 – Snapshot Server Scope & Dynamic Completeness  
**Baseline:** v0.9.5.72 – Documentation Consolidation & Project Handover  
**Updated:** 2026-07-03

This file is now the canonical release-note ledger for Sentinel. Older release-note fragments in `/docs` are legacy sources; future releases should update this document directly.


## v0.9.5.74 – Snapshot Server Scope & Dynamic Completeness

### Purpose
Replace fragile free-text expected-server handling with explicit snapshot server scope. Completeness is now calculated against the snapshot's intended scope instead of any fixed global server count.

### Included changes
- Added `ServerScope` model with `all`, `range` and `selected` modes.
- Added range expansion so `549–676` becomes 128 expected servers without manual entry.
- Kept selected-server mode for small events and special cases.
- Added controlled snapshot editing for `open`, `importing` and `review` snapshots.
- Locked completed/closed/archived snapshots against scope edits.
- Added snapshot edit audit metadata for scope/ranking changes.
- Bound import reports now include explicit `snapshot_server_scope` metadata.
- Snapshot coverage now exposes expected feed count, valid imported feed count and completeness percentage.
- Import Center UI now creates and edits snapshots through Server Scope instead of ambiguous expected-server text.

### Validation
```text
pytest tests/smoke/test_snapshot_management.py tests/smoke/test_snapshot_upload_binding.py -q
7 passed

python -m compileall -q application/snapshots web/routes/imports.py version.py
```

### Commit
```bash
git add .
git commit -m "feat(snapshot): add server scope and dynamic completeness"
git tag -a v0.9.5.74 -m "v0.9.5.74 Snapshot Server Scope and Dynamic Completeness"
```

## v0.9.5.73 – Snapshot Upload Binding & Import Context Enforcement

### Focus
Make managed snapshots unavoidable for screenshot imports and bind Current Run artifacts to the active import context before any strategic interpretation.

### Added
- Active snapshot gate in `main.py` for screenshot import.
- Snapshot-bound default export path under `output/snapshots/<snapshot_id>/lastwar_export.xlsx`.
- Import report snapshot binding metadata with schema `sentinel.import_run.v2`.
- Snapshot-level coverage model for expected rankings, expected servers, imported feeds, missing combinations and open reviews.
- Import Center active snapshot coverage panel and unbound-report warning.
- Review evidence and persistent Review History snapshot id/name propagation.
- Smoke tests for snapshot requirement, report binding, missing-feed coverage and review-history binding.

### Changed
- Screenshot import now blocks when no active `screenshot_upload` snapshot exists.
- Closed, complete or non-screenshot snapshots cannot receive screenshot imports.
- Latest import report is no longer treated as current phase evidence when it is not bound to the active snapshot.
- Snapshot creation can optionally record expected servers, allowing server/ranking missing-feed checks.

### Guardrail
Snapshot binding is audit context only. It does not promote rows into Operational Truth, does not merge Historical Dataset with Current Run, and does not use screenshot filename/order/upload order as truth.

### Validation
```text
pytest tests/smoke/test_snapshot_management.py tests/smoke/test_snapshot_upload_binding.py tests/smoke/test_command_center.py -q
10 passed

python -m compileall -q application/snapshots services/command_center.py web/routes/imports.py main.py tests/smoke/test_snapshot_upload_binding.py
```

### Commit
```bash
git add .
git commit -m "feat(import): enforce snapshot-bound screenshot imports"
git tag -a v0.9.5.73 -m "v0.9.5.73 Snapshot Upload Binding and Import Context Enforcement"
```

## v0.9.5.72 – Documentation Consolidation & Project Handover

### Added
- Consolidated documentation handoff for the current Sentinel architecture.
- Added `docs/NEXT_CHAT.md` with a copy/paste start prompt for the next development chat.
- Added official documentation for the Snapshot Management concept and its role as the future container for screenshot uploads, reviews, exports, coverage and later intelligence.
- Added documented project philosophy: **Data Quality before Intelligence**.

### Changed
- Updated project status, road to v1, modus operandi, architectural decisions and lessons learned to reflect the sprint line from v0.9.5.47 through v0.9.5.71.
- Consolidated patch-summary handling into `docs/PATCH_SUMMARY.md` as the ongoing canonical document.
- Clarified that Historical Dataset, Current Run, Benchmark/Ground Truth and Operational Truth must not be mixed.

### Guardrails
- Documentation-only release. No OCR, Data Guard, Ranking Guard, export, import or web runtime behavior changed.
- Operational Truth remains protected by Data Guard and Human Review.

### Validation
```text
Documentation structure reviewed.
Core handoff documents updated.
Version updated to 0.9.5.72.
```

### Commit
```bash
git add .
git commit -m "docs(project): consolidate Sentinel handoff documentation for v0.9.5.72"
git tag -a v0.9.5.72 -m "v0.9.5.72 Documentation Consolidation and Project Handover"
```

## Recent release context

### v0.9.5.71 – Snapshot Management Foundation
Introduced managed snapshot context as the planned container for screenshot upload batches such as `S6 pre Transfer`. The current implementation provides a JSON-backed snapshot service and Import Center controls. The concept must be expanded in the next product phase so every screenshot import belongs to an explicit snapshot.

### v0.9.5.70 – Historical Import Integrity & Coverage Drilldown
Made historical Excel coverage visible and auditable in the Command Center/Import Center. Historical data is reference coverage only; it does not overwrite Operational Truth.

### v0.9.5.69 – Historical Import Performance Fix
Fixed the historical Excel importer from multi-minute execution to seconds by using bulk behavior, progress output and relevant sheet handling.

### v0.9.5.66–0.9.5.68 – Operational Readiness and Historical Baseline
Added Operational Readiness drilldowns, corrected current-run/historical/benchmark separation, and imported historical Excel coverage as a baseline for 128 known servers.

### v0.9.5.62–0.9.5.65 – Review UX and Screenshot Evidence
Consolidated visible navigation, linked screenshot evidence, added review screenshot previews and calibrated rank highlight overlays.

### v0.9.5.55–0.9.5.61 – Command Center and Human Review Workflow
Introduced Command Center, Review Dashboard, Review Evidence Pack, explainable review messages, persistent review history and first resolution-state foundation.

### v0.9.5.47–0.9.5.54 – Data Integrity Fortress
Built context-aware power recovery, reportable candidate metadata, ranking guard recovery, review OCR, bounded row reconstruction and guard-driven quarantine handling.

# Consolidated legacy release-note sources

---

## Legacy source: `RELEASE_NOTES_PATCH10A.md`

# Sentinel v0.9.5.30 – Universal Server Detection

## Focus

Generalize server detection for mobile and localized screenshots without changing OCR, parser, Data Guard, Ranking Guard, Recovery, or Inference behavior.

The blind Server 552 mobile test showed that German mobile screenshots expose server evidence as repeated row-level values such as `Kriegszone #552`, while the existing detector was still Warzone/header-oriented. Sentinel correctly moved all screenshots to review instead of guessing, but the candidate extractor failed to surface the already-visible `#552` evidence.

## Added

- Pattern-first server candidate extraction for language-neutral `#123` / `#1234` OCR tokens.
- Support for full-width `＃` hash tokens.
- Localized fallback patterns for common labels such as `Kriegszone`, `Zona`, and `Zone de guerre`.
- Smoke tests for:
  - repeated mobile `#552` candidates,
  - localized `Kriegszone #552` candidates,
  - ambiguous hash candidates that must remain review.

## Changed

- Server candidate extraction now collects hash-number candidates before language-specific label patterns.
- Existing consensus and Data Guard logic remain authoritative.
- Version updated to `0.9.5.30`.

## Guardrail

This release does not guess a server from filenames, timestamps, upload source, or session context.

A server is accepted only when repeated intrinsic OCR evidence reaches the existing consensus threshold. Ambiguous or insufficient candidates still go to review.

## Validation

```text
python -m pytest tests/smoke/test_warzone_consensus.py tests/smoke/test_sentinel_data_guard.py tests/smoke/test_operational_import_repository.py -q
11 passed
```

## Commit

```bash
git add .
git commit -m "feat(server): add pattern-based universal server detection"
git tag -a v0.9.5.30 -m "v0.9.5.30 Universal Server Detection"
```

---

# Sentinel v0.9.5.29 – Ranking Guard Recovery

## Focus

Introduces a conservative Ranking Guard Recovery layer after the Ranking Guard and before quarantine.

The goal is not to guess corrected rankings. The goal is to recover only rows whose ranking-type assignment is provably safe, and to calibrate false-positive alliance-name shapes that previously filled quarantine.

## Added

- `parser/ranking_recovery.py`
  - Evidence-based recovery decisions for Ranking Guard quarantines.
  - Explicit distinction between `recovered`, `calibrated_pass`, and `quarantine`.
  - Safe THP recovery only when explicit player fields and player-scale power are present.
  - Alliance Power calibration for rows where bracketed alliance names mimic player tags but no explicit player fields exist.
- Ranking recovery metrics in `data/latest_import_report.json`:
  - attempts,
  - success,
  - calibrated_pass,
  - rejected,
  - confidence_avg.
- Smoke tests for Ranking Guard Recovery.

## Changed

- `parser/ranking_guard.py` now gives the recovery layer one conservative chance before quarantine.
- Ranking Guard remains the integrity gate; Recovery cannot bypass it.
- Rows recovered or calibrated by the recovery layer are annotated with explainable evidence fields.
- Version updated to `0.9.5.29`.

## Guardrail

Recovery is evidence-based only.

A row is not moved because it is convenient. It is moved only if row-level evidence proves a safer destination. If evidence is insufficient, quarantine remains the correct outcome.

## Validation

```text
python -m pytest tests/smoke/test_ranking_recovery.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_operational_import_repository.py -q
```

## Commit

```bash
git add .
git commit -m "feat(ranking): add evidence-based ranking guard recovery"
git tag -a v0.9.5.29 -m "v0.9.5.29 Ranking Guard Recovery"
```


# v0.9.5.35 – THP Power Sanity Guard

Adds a conservative THP-only sanity guard that quarantines late-scroll power outliers before final rank merge. This protects Operational Truth from OCR digit spikes while keeping OCR and parser behavior unchanged.

---

## Legacy source: `RELEASE_NOTES_v0.9.5.30.md`

# Sentinel v0.9.5.30 – Universal Server Detection

## Focus

Generalize server detection for mobile and localized screenshots without changing OCR, parser, Data Guard, Ranking Guard, Recovery, or Inference behavior.

The blind Server 552 mobile test showed that German mobile screenshots expose server evidence as repeated row-level values such as `Kriegszone #552`, while the existing detector was still Warzone/header-oriented. Sentinel correctly moved all screenshots to review instead of guessing, but the candidate extractor failed to surface the already-visible `#552` evidence.

## Added

- Pattern-first server candidate extraction for language-neutral `#123` / `#1234` OCR tokens.
- Support for full-width `＃` hash tokens.
- Localized fallback patterns for common labels such as `Kriegszone`, `Zona`, and `Zone de guerre`.
- Smoke tests for:
  - repeated mobile `#552` candidates,
  - localized `Kriegszone #552` candidates,
  - ambiguous hash candidates that must remain review.

## Changed

- Server candidate extraction now collects hash-number candidates before language-specific label patterns.
- Existing consensus and Data Guard logic remain authoritative.
- Version updated to `0.9.5.30`.

## Guardrail

This release does not guess a server from filenames, timestamps, upload source, or session context.

A server is accepted only when repeated intrinsic OCR evidence reaches the existing consensus threshold. Ambiguous or insufficient candidates still go to review.

## Validation

```text
python -m pytest tests/smoke/test_warzone_consensus.py tests/smoke/test_sentinel_data_guard.py tests/smoke/test_operational_import_repository.py -q
11 passed
```

## Commit

```bash
git add .
git commit -m "feat(server): add pattern-based universal server detection"
git tag -a v0.9.5.30 -m "v0.9.5.30 Universal Server Detection"
```

---

## Legacy source: `RELEASE_NOTES_v0.9.5.31.md`

# Sentinel v0.9.5.31 – Mobile Ranking Type Integrity Hotfix

## Focus

Fixes a blind-test issue found on Server 552 mobile German screenshots where lower Alliance Power pages were inferred as Total Hero Power after their values dropped below 1B.

## Fixed

- Detects German mobile ranking headers:
  - `Allianz-Kampfkraft` → `alliance_power`
  - `Gesamtkampfkraft der Helden` → `total_hero_power`
- Prevents low-rank Alliance Power rows from leaking into THP merely because their values are player-scale.
- Keeps genuine low-rank Alliance Power rows in Alliance Power when the source screen is classified as Alliance Power and the row has alliance-name-only shape.
- Keeps top-rank THP-shaped rows in Alliance Power quarantined instead of blindly accepting them.

## Guardrail

This patch does **not** weaken the Data Guard doctrine. It does not guess a ranking type from filenames or timestamps. It uses intrinsic screen/header evidence and conservative row-shape calibration.

## Validation

```text
10 passed
```

Targeted tests:

```bash
pytest tests/smoke/test_mobile_german_ranking_type_detection.py \
       tests/smoke/test_ranking_recovery.py \
       tests/smoke/test_sentinel_ranking_guard.py \
       tests/smoke/test_ranking_type_fallback.py -q
```

## Commit

```bash
git add .
git commit -m "fix(import): preserve mobile alliance ranking type integrity"
git tag -a v0.9.5.31 -m "v0.9.5.31 Mobile Ranking Type Integrity Hotfix"
```

---

## Legacy source: `RELEASE_NOTES_v0.9.5.32.md`

# Sentinel v0.9.5.32 – Semantic Ranking Guard

## Focus

Fixes the remaining mobile Server 552 ranking-type integrity issue by making the Ranking Guard semantic instead of power-threshold driven.

## Fixed

- Bracketed alliance names such as `[drr] Young Tokai Teio` are no longer treated as player evidence by themselves.
- Low-power Alliance Power rows below 1B are allowed when they come from an Alliance Power screen and only contain generic alliance-name fields.
- THP rows still require explicit player-ranking fields (`alliance_tag`, `player_name`, or `hero_power`) before they can be recovered into `total_hero_power`.
- German column headers are now accepted as ranking-type evidence:
  - `Allianzname` → `alliance_power`
  - `Kommandant` → `total_hero_power`

## Changed

- Ranking Guard scoring now separates explicit player fields from bracketed tags inside generic alliance names.
- Power remains supporting evidence only; it is no longer sufficient to classify low-power alliance rows as THP.
- Existing Ranking Recovery remains conservative and only reclassifies rows when explicit player fields are present.

## Validation

```text
pytest tests/smoke/test_semantic_ranking_guard.py \
       tests/smoke/test_mobile_german_ranking_type_detection.py \
       tests/smoke/test_sentinel_ranking_guard.py \
       tests/smoke/test_ranking_recovery.py -q

16 passed
```

Full smoke collection still contains pre-existing invalid legacy smoke files unrelated to this patch.

## Commit

```bash
git add .
git commit -m "fix(ranking): add semantic Ranking Guard field evidence"
git tag -a v0.9.5.32 -m "v0.9.5.32 Semantic Ranking Guard"
```

---

## Legacy source: `RELEASE_NOTES_v0.9.5.34.md`

# Sentinel v0.9.5.34 – Mobile Ranking Boundary Hotfix

## Focus

Fixes a mobile German Total Hero Power detection issue where generic `Allianzname` column evidence could outweigh `Kommandant` player-ranking evidence.

## Fixed

- Ranking type detection is now evidence-scored instead of first-match based.
- `Kommandant` / `Commander` evidence wins over generic alliance-name column labels on THP screens.
- `Allianz-Kampfkraft` remains strong Alliance Power title evidence.
- Prevents the first mobile THP screenshot from being appended to the Alliance Power sheet.

## Validation

```text
pytest tests/smoke/test_mobile_german_ranking_type_detection.py tests/smoke/test_semantic_ranking_guard.py -q
```

## Commit

```bash
git add .
git commit -m "fix(ranking): prioritize commander evidence for mobile THP screens"
git tag -a v0.9.5.34 -m "v0.9.5.34 Mobile Ranking Boundary Hotfix"
git push origin main
git push origin v0.9.5.34
```

---

## Legacy source: `RELEASE_NOTES_v0.9.5.35.md`

# Sentinel v0.9.5.35 – THP Power Sanity Guard

## Focus

Protect Total Hero Power exports from OCR digit outliers that are locally inconsistent with their screenshot context.

## Fixed

- Prevents late-scroll THP OCR spikes such as `198M -> 798M` from being promoted to top ranks by the final power-order merge.
- Suspicious THP values are quarantined with explainable `thp_power_sanity` evidence instead of being silently imported.
- Keeps valid first-screen THP whales untouched; the guard only applies to later THP screenshots with local outlier evidence.

## Added

- `parser/thp_sanity_guard.py`
- THP local median outlier detection.
- Quarantine metadata:
  - `quarantine_reason = thp_power_sanity_outlier`
  - `ranking_guard_warning = thp_power_sanity:...`
  - `thp_sanity_local_median`
- Smoke tests for:
  - late-scroll THP outlier quarantine,
  - real first-screen whales allowed,
  - normal scroll overlap allowed.

## Validation

```text
python -m compileall -q parser main.py
pytest tests/smoke/test_thp_power_sanity_guard.py tests/smoke/test_semantic_ranking_guard.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_mobile_german_ranking_type_detection.py tests/smoke/test_power_first_reconstruction.py -q
16 passed
```

## Commit

```bash
git add .
git commit -m "fix(data-guard): quarantine THP power outliers before rank merge"
git tag -a v0.9.5.35 -m "v0.9.5.35 THP Power Sanity Guard"
git push origin main
git push origin v0.9.5.35
```

---

## Legacy source: `RELEASE_NOTES_v0.9.5.36.md`

# Sentinel v0.9.5.36 – Ranking Power Monotonicity Guard

## Focus

Generalize the THP Power Sanity Guard into a ranking-wide power envelope guard.

This release protects both `total_hero_power` and `alliance_power` exports from OCR digit outliers before the final power-order merge can promote impossible values to the top of a ranking.

## Fixed

- Prevents Alliance Power OCR spikes such as `23B -> 79B` from being promoted to top ranks.
- Keeps legitimate low-power alliance tail ranks below 1B intact.
- Preserves v0.9.5.35 THP behavior for late-scroll `198M -> 798M`-style outliers.
- Adds rank-aware grace for genuine top Alliance Power leaders.

## Added

- `parser/ranking_power_sanity_guard.py`
- Generic local power-envelope validation for guarded ranking types.
- Alliance Power outlier quarantine metadata:
  - `quarantine_reason = alliance_power_sanity_outlier`
  - `ranking_guard_warning = power_sanity:alliance_power_outlier;...`
  - `power_sanity_local_median`
  - `power_sanity_local_ratio`
- Backward-compatible `parser/thp_sanity_guard.py` wrapper.
- Smoke tests for:
  - Alliance Power local outlier quarantine,
  - legitimate low-power Alliance Power tails,
  - real rank-1 Alliance Power leaders,
  - existing THP sanity guard behavior.

## Validation

```text
python -m compileall -q parser main.py
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_thp_power_sanity_guard.py tests/smoke/test_semantic_ranking_guard.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_mobile_german_ranking_type_detection.py tests/smoke/test_power_first_reconstruction.py -q
19 passed
```

## Commit

```bash
git add .
git commit -m "fix(data-guard): quarantine ranking power outliers before merge"
git tag -a v0.9.5.36 -m "v0.9.5.36 Ranking Power Monotonicity Guard"
git push origin main
git push origin v0.9.5.36
```

---

## Legacy source: `RELEASE_NOTES_v0.9.5.37.md`

# Sentinel v0.9.5.37 – Screenshot-Aware Ranking Power Guard

## Focus

Turns the Ranking Power Guard from a strict local median filter into a screenshot/rank-aware context validator.

## Fixed

- Legitimate top-3 Alliance Power rows are no longer quarantined when mobile screenshots split the top ranks across adjacent captures.
- Server 552 Alliance Power top rows such as 79B / 77B / 70B are allowed when rank context marks them as true top ranks.
- Lower-rank Alliance Power OCR explosions remain quarantined before power sorting.
- THP Power Sanity behavior from v0.9.5.35 remains unchanged.

## Guardrails

- Added an absolute Alliance Power ceiling so catastrophic top-rank digit explosions are still quarantined.
- Quarantine remains preferred over silent correction.

## Validation

```text
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_thp_power_sanity_guard.py tests/smoke/test_semantic_ranking_guard.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_mobile_german_ranking_type_detection.py tests/smoke/test_power_first_reconstruction.py -q
```

---

## Legacy source: `RELEASE_NOTES_v0.9.5.38.md`

# Sentinel v0.9.5.38 – Top Rank Alliance Power Allowance

## Focus

Fixes an over-conservative Ranking Power Sanity Guard decision where real top Alliance Power rows from early mobile screenshots were quarantined because OCR rank anchors were missing before final reconstruction.

## Fixed

- Allows very high Alliance Power values in the first two Alliance Power source screenshots even when `ocr_rank` is missing.
- Keeps the absolute Alliance Power safety ceiling in place.
- Keeps late-source Alliance Power outlier quarantine active.
- Keeps THP Power Sanity behavior unchanged.

## Why

Mobile screenshots may split the real Top 3 Alliance Power rows across the first two source images. Before final export, those rows can lack rank anchors, so a rank-only Top 3 exception is not enough. Sentinel now treats early screenshot source position as supporting context while still quarantining late-scroll explosions.

## Validation

```text
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_thp_power_sanity_guard.py tests/smoke/test_semantic_ranking_guard.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_mobile_german_ranking_type_detection.py tests/smoke/test_power_first_reconstruction.py -q
```

## Commit

```bash
git add .
git commit -m "fix(ranking-guard): allow early top alliance power rows without rank anchors"
git tag -a v0.9.5.38 -m "v0.9.5.38 Top Rank Alliance Power Allowance"
```

---

## Legacy source: `RELEASE_NOTES_v0.9.5.39.md`

# Sentinel v0.9.5.39 – General Top Alliance Power Allowance

## Focus

Finalizes the Ranking Power Sanity Guard behavior for multi-server regression runs.

## Fixed

- Generalizes the top Alliance Power allowance introduced for Server 552 so it also protects legitimate top-of-source rows from desktop captures.
- Prevents real leading alliances such as strong Server 550/551 Alliance Power rows from being quarantined only because their screenshot-local median is much lower.
- Preserves quarantine behavior for late-row Alliance Power spikes and late-scroll THP OCR outliers.

## Validation

```text
pytest tests/smoke/test_ranking_power_sanity_guard.py -q
pytest tests/smoke -q
```

Expected operational validation:

```text
python main.py
python ground_truth_validator.py
```

## Commit

```bash
git add .
git commit -m "fix(ranking): generalize top alliance power allowance"
git tag -a v0.9.5.39 -m "v0.9.5.39 General Top Alliance Power Allowance"
```

---

## Legacy source: `RELEASE_NOTES_v0.9.5.40.md`

# Sentinel v0.9.5.40 – Alliance Power Shape Guard

## Focus

Finalizes the Alliance Power power-sanity path after the 68-screenshot regression run showed that simple top-of-source allowances were too broad.

## Fixed

- Blocks source-local 50B+ Alliance Power high clusters such as the false Server 552 `79B / 77B / 70B` OCR spikes.
- Keeps legitimate lower Alliance Power leaders such as Server 550 `WARF / LsC` and Server 551 `Hsg` out of quarantine.
- Avoids using global screenshot order, filenames, timestamps, or cross-user batch order as truth.
- Preserves the existing THP late-scroll outlier guard.
- Keeps absolute Alliance Power ceiling protection.

## Added

- Source-local Alliance Power shape detector in `parser/ranking_power_sanity_guard.py`.
- Regression coverage for false 552 high clusters and legitimate 550/551 top-of-source rows.
- More explicit `source_shape_high_cluster` quarantine evidence.

## Validation

```text
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_thp_power_sanity_guard.py tests/smoke/test_semantic_ranking_guard.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_mobile_german_ranking_type_detection.py tests/smoke/test_power_first_reconstruction.py -q
25 passed
```

## Commit

```bash
git add .
git commit -m "fix(ranking-guard): add alliance power source-shape sanity guard"
git tag -a v0.9.5.40 -m "v0.9.5.40 Alliance Power Shape Guard"
```

---

## Legacy source: `RELEASE_NOTES_v0.9.5.41.md`

# Sentinel v0.9.5.41 – High-Cluster Alliance Power Guard

## Focus

Finalizes the Alliance Power source-shape guard for paired high OCR spikes.

## Fixed

- Blocks paired 50B+ Alliance Power OCR spikes at the top of a single source when the remaining visible source envelope is far lower.
- Extends the v0.9.5.40 source-shape guard so 552-style `79B / 77B / 70B` false high cluster is fully quarantined.
- Keeps legitimate 550/551 Alliance Power leaders such as `WARF`, `LsC`, and `Hsg` allowed.
- Keeps THP outlier behavior unchanged.

## Guardrail

The guard remains source-local. It does not rely on screenshot filename order, upload order, or multi-user batch order.

## Validation

```text
python -m compileall -q parser main.py ground_truth_validator.py sentinel.py
pytest tests/smoke/test_ranking_power_sanity_guard.py -q
9 passed
```

Full test collection still contains pre-existing legacy smoke-test issues unrelated to this patch.

---

## Legacy source: `RELEASE_NOTES_v0.9.5.42.md`

# Sentinel v0.9.5.42 – Ranking Segment Integrity Guard

## Focus

Protect ranking reconstruction from scroll-segment contamination without relying on screenshot filename order.

## Added

- Intrinsic THP rank/power envelope guard.
- Late-scroll THP rows with high OCR ranks and impossible top-whale powers are quarantined before final power sorting.
- Alliance Power rank/power envelope guard for non-top rows with impossible 50B+ values.
- Explainable quarantine reasons:
  - `thp_rank_power_envelope_violation`
  - `alliance_rank_power_envelope_violation`

## Why

Server 553 showed a new failure mode: late-scroll THP screenshots containing ranks around 100 were parsed with OCR digit explosions around 764M and then sorted above the real Rank 1 player. Earlier guards relied too much on source order, which is unsafe when future Discord or multi-user uploads can mix screenshots from different rankings.

This patch uses row-intrinsic evidence instead: OCR rank plus parsed power. A row that claims to be Rank 100 but carries a top-whale power value is not trusted. It is quarantined, not repaired.

## Expected impact

- Server 553 false THP leaders such as late-rank 764M rows should move to `REVIEW - ranking_guard_quarantine`.
- Server 553 Alliance Power false 77B non-top row should be quarantined.
- Existing 549–552 protections remain intact because the guard is intrinsic and conservative.

## Validation

```text
python -m compileall -q parser main.py ground_truth_validator.py
python main.py
python ground_truth_validator.py
```

## Commit

```bash
git add .
git commit -m "fix(ranking-guard): add intrinsic segment integrity guard"
git tag -a v0.9.5.42 -m "v0.9.5.42 Ranking Segment Integrity Guard"
git push origin main
git push origin v0.9.5.42
```

---

## Legacy source: `RELEASE_NOTES_v0.9.5.43.md`

# Sentinel v0.9.5.43

## Fix

Adds a THP source-shape digit explosion guard.

The guard detects a mixed screenshot source where late-scroll rows around ~160M THP are present, but neighbouring rows from the same source are misread as ~760M/~790M and incorrectly jump to the top after power sorting.

## Principles

- Source-local only.
- No reliance on screenshot order, upload order, or filename order as truth.
- OCR rank remains weak evidence.
- Rank-conflict evidence is required before the high cluster is blocked.
- Quarantine remains preferred over false operational truth.

## Validation

```text
26 passed
```

---

## Legacy source: `RELEASE_NOTES_v0.9.5.44.md`

# Sentinel v0.9.5.44

## Focus

Targeted Ranking Power Sanity Guard hardening for Server 553 imports.

## Fixed

- Quarantines complete THP digit-explosion clusters when one row in the same impossible high cluster lacks a rank-conflict warning.
- Prevents a false 7xx-M THP row from surviving as rank 1 after adjacent 7xx-M rows are already quarantined.
- Quarantines source-local Alliance Power middle spikes such as a 77B value appearing after lower visible rank-1..4 rows in the same screenshot.
- Keeps the rule source-local: no reliance on screenshot filename order, upload order, or cross-user screenshot sequence.

## Why

Server 553 showed two remaining failure classes:

1. THP rows from late-scroll screenshots could be OCR-read as 7xx-M values and jump to the top after sorting.
2. Alliance Power values could gain an extra leading digit inside the same visible screenshot block, e.g. an 11.7B row becoming 77.7B.

Both are intrinsic source-shape problems, not server-order problems.

## Validation

```text
pytest tests/smoke/test_ranking_power_sanity_guard.py -q
11 passed
```

## Commit

```bash
git add .
git commit -m "fix(ranking-guard): harden source-local power sanity for v0.9.5.44"
git tag -a v0.9.5.44 -m "v0.9.5.44 Source-local Power Sanity Guard"
```

---

## Legacy source: `RELEASE_NOTES_v0.9.5.45.md`

# Sentinel v0.9.5.45

## Focus

Field-level power recovery for mobile OCR leading-digit explosions.

## Added

- Source-local leading-digit recovery for THP values such as `764,292,586 -> 164,292,586` when rank/source context supports the correction.
- Source-local leading-digit recovery for Alliance Power values such as `77,739,565,950 -> 17,739,565,950` when the row is not a valid top-3 leader and the recovered value fits the local ranking envelope.
- Recovery metadata on corrected rows:
  - `power_original`
  - `power_recovered_from`
  - `power_recovery_method`
  - `power_sanity_status=recovered`

## Changed

- Ranking Power Sanity Guard no longer only quarantines this specific recoverable OCR class.
- Values are recovered only when intrinsic rank/source evidence is strong enough.
- The guard still quarantines suspicious values when no safe recovery candidate exists.

## Why

Server 553 proved that the v0.9.5.44 guard correctly identified false 7xx-M THP and 77B Alliance Power values, but it preserved them only in quarantine. The screenshots show that many of these values are recoverable leading-digit OCR errors rather than unusable rows.

Sentinel should not invent truth. But when the source-local evidence supports a deterministic field-level recovery, preserving the row with explicit recovery metadata is better than dropping useful data into review.

## Validation

```text
python -m compileall -q parser main.py version.py
pytest tests/smoke/test_ranking_power_sanity_guard.py tests/smoke/test_thp_power_sanity_guard.py tests/smoke/test_sentinel_ranking_guard.py tests/smoke/test_ranking_recovery.py -q
22 passed
```

## Commit

```bash
git add .
git commit -m "fix(ranking-guard): recover source-local leading digit power errors"
git tag -a v0.9.5.45 -m "v0.9.5.45 Source-local Power Digit Recovery"
```

---

## Legacy source: `docs_RELEASE_NOTES_v0.9.5.17.md`

# Sentinel v0.9.5.17 – Gap Resolver

## Focus
Active resolution of recoverable validation gaps caused by screenshot/server bucket leakage.

## Added
- `parser/gap_resolver.py`
- Cross-server gap candidate search for rows exported under the wrong server sheet
- Conservative evidence scoring using power, normalized name, and alliance compatibility
- `gap_resolved_rows` validation metric
- Smoke tests for gap resolver and validator integration

## Improved
- Recoverable gaps are no longer just annotated; high-confidence candidates can now be pulled back into the correct Ground Truth row.
- Wrong rank fallbacks remain blocked unless strong evidence exists.

## Server 551 Benchmark
- Valid matches: 36 → 43
- Bad matches: 13 → 6
- Gap rows: 14 → 7
- Gap resolved rows: 7
- Precision: 0.7500 → 0.8958
- Recall: 0.7200 → 0.8600
- F1: 0.7347 → 0.8775
- Usable identities: 26 → 32
- Score: 53.69 → 63.45



---

# Sentinel v0.9.5.83 – Recognition Engine Pass I / Rebuild Telemetry Hotfix

## Focus

Stabilize the developer/report rebuild path introduced during the recognition-quality work so quick tests do not require a full 99-screenshot OCR run.

## Fixed

- `python main.py --rebuild-reports` no longer crashes with `UnboundLocalError: runtime_timings`.
- Runtime telemetry is initialized at the start of `main()` and is now available in both the normal import path and report-rebuild path.
- Rebuild mode now prints timing telemetry and runtime duration without touching OCR, screenshots, snapshot state, Excel export or Operational Truth.

## Added

- Smoke coverage for `--rebuild-reports` to ensure the fast report-only feedback loop remains available.

## Why

The 99-screenshot benchmark is too expensive to run after every UI/report change. Sentinel needs reliable short-loop developer commands before more recognition-engine changes are attempted. This patch repairs that loop and keeps the large benchmark reserved for changes that should move recognition metrics.

## Validation

```text
pytest tests/smoke/test_developer_run_modes.py -q
python -m compileall -q main.py services parser application version.py
zip integrity OK
```

## Commit

```bash
git add .
git commit -m "fix(dev): initialize rebuild report telemetry"
git tag -a v0.9.5.83 -m "v0.9.5.83 Rebuild Report Telemetry Hotfix"
```


## v0.9.5.87 – Data Quality Stabilization

- Defaulted Sentinel to Development/Truth-First mode: OCR cache is disabled unless explicitly enabled with `--ocr-cache`, `SENTINEL_OCR_CACHE=1`, or production mode.
- Added pending review placeholders so quarantined ranking rows keep their operational rank slot instead of silently collapsing following ranks upward.
- Preserved observed identity fields for pending rows (`observed_name`, `observed_alliance`) so review display can distinguish raw screenshot evidence from normalized matching values.
- Updated recognition-quality decision version to v0.9.5.87.
- Added regression coverage for development-mode cache behavior and pending slot preservation.

---

## Consolidated legacy release-note sources

The following legacy release-note files remain in `/docs` for traceability, but `docs/RELEASE_NOTES.md` is the canonical ledger going forward:

- `RELEASE_NOTES_PATCH10A.md`
- `RELEASE_NOTES_v0.9.5.30.md` through `RELEASE_NOTES_v0.9.5.45.md`
- `docs_RELEASE_NOTES_v0.9.5.17.md`

Future sprints should add new notes to this file first. Legacy files should not be extended unless a migration audit requires it.
